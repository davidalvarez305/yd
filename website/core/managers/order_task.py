from django.core.exceptions import ValidationError
from typing import Optional
from dataclasses import dataclass
from django.db import transaction
from django.template.loader import render_to_string

from core.models import OrderTask, OrderTaskChoices, OrderTaskStatus, OrderTaskStatusChoices, User, Order, OrderTaskStatusChangeHistory
from core.email import email_service
from website import settings

class InvalidTaskTransitionError(ValidationError):
    """Raised when an invalid task state transition is attempted."""
    pass

@dataclass
class TaskTransitionContext:
    user: Optional[User] = None
    task: Optional[OrderTask] = None
    source: str = "system"

class OrderTaskManager:
    TRANSITIONS = {
        OrderTaskStatusChoices.ASSIGNED: [
            OrderTaskStatusChoices.IN_PROGRESS,
            OrderTaskStatusChoices.UNABLE_TO_COMPLETE,
        ],
        OrderTaskStatusChoices.IN_PROGRESS: [
            OrderTaskStatusChoices.COMPLETED,
            OrderTaskStatusChoices.UNABLE_TO_COMPLETE,
        ],
        OrderTaskStatusChoices.UNABLE_TO_COMPLETE: [],
        OrderTaskStatusChoices.COMPLETED: [],
    }

    TERMINAL_STATUSES = {
        OrderTaskStatusChoices.COMPLETED,
        OrderTaskStatusChoices.UNABLE_TO_COMPLETE,
    }

    def __init__(self, order_task: OrderTask):
        self.order_task = order_task

    @property
    def current_log(self) -> OrderTaskStatusChangeHistory | None:
        return (
            OrderTaskStatusChangeHistory.objects
            .filter(order_task=self.order_task)
            .select_related("order_task_status")
            .order_by("-date_created")
            .first()
        )

    @property
    def current_status(self) -> str | None:
        return self.current_log.order_task_status.status if self.current_log else None

    def allowed_transitions(self) -> list[str]:
        if not self.current_status:
            return []
        return self.TRANSITIONS.get(self.current_status, [])

    def can_transition_to(self, new_status: str) -> bool:
        if not self.current_status:
            return True
        return new_status in self.allowed_transitions()

    @transaction.atomic
    def transition_to(self, new_status: str, user: User, context: TaskTransitionContext | None = None, notes: str | None = None) -> OrderTaskStatusChangeHistory:
        context = context or TaskTransitionContext(user=user, task=self.order_task, source="user")

        if self.current_status in self.TERMINAL_STATUSES:
            raise InvalidTaskTransitionError(
                f"Task already terminal ({self.current_status})"
            )

        if self.current_status and not self.can_transition_to(new_status):
            raise InvalidTaskTransitionError(
                f"Cannot transition task from '{self.current_status}' to '{new_status}'"
            )

        status = OrderTaskStatus.objects.get(status=new_status)

        log = OrderTaskStatusChangeHistory.objects.create(
            order_task=self.order_task,
            order_task_status=status,
            notes=notes,
        )

        self._run_hooks(new_status, context)

        return log
    
    def _run_hooks(self, new_status: str, context: TaskTransitionContext):
        match new_status:
            case OrderTaskStatusChoices.ASSIGNED:
                self._on_assigned(context)
            case OrderTaskStatusChoices.IN_PROGRESS:
                self._on_in_progress(context)
            case OrderTaskStatusChoices.COMPLETED:
                self._on_completed(context)
            case OrderTaskStatusChoices.UNABLE_TO_COMPLETE:
                self._on_unable_to_complete(context)

    def _on_assigned(self, context: TaskTransitionContext):
        self._notify_user_task_assigned()

    def _on_in_progress(self, context: TaskTransitionContext): pass

    def _on_completed(self, context: TaskTransitionContext):
        match self.order_task.task.task:
            case OrderTaskChoices.LOAD_ORDER_ITEMS:
                self.order_task.order.manager.mark_ready_for_dispatch(context.user)

            case OrderTaskChoices.UNLOAD_ORDER_ITEMS:
                self.order_task.order.manager.finalize()

    def _on_unable_to_complete(self, context: TaskTransitionContext): pass

    def assign_task(self, user: User, context: TaskTransitionContext | None = None, notes: str | None = None) -> OrderTaskStatusChangeHistory:
        return self.transition_to(
            OrderTaskStatusChoices.ASSIGNED,
            user=user,
            context=context,
            notes=notes,
        )
    
    def complete_task(self, user: User, context: TaskTransitionContext | None = None, notes: str | None = None) -> OrderTaskStatusChangeHistory:
        return self.transition_to(
            OrderTaskStatusChoices.COMPLETED,
            user=user,
            context=context,
            notes=notes,
        )
    
    def _notify_user_task_assigned(self):
        html = render_to_string(
            "emails/notify_user_task_assigned.html",
            {
                "items": self.order_task.order.items.all(),
                "order_code": self.order_task.order.code,
                "start_date": self.order_task.order.start_date.strftime("%B %d, %Y"),
                "end_date": self.order_task.order.end_date.strftime("%B %d, %Y"),
            }
        )

        email_service.send_html_email(
            to=self.order_task.user.email,
            subject=f"Tasked Assigned for Order: {self.order_task.order.code}",
            html=html,
        )