from django.core.exceptions import ValidationError
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from django.db import transaction

from core.models import OrderTask, OrderTaskStatus, OrderTaskStatusChoices, User, Order, OrderTaskLog

class InvalidTaskTransitionError(ValidationError):
    """Raised when an invalid task state transition is attempted."""
    pass

@dataclass
class TaskTransitionContext:
    user: Optional[User] = None
    order: Optional[Order] = None
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

    def __init__(self, order: Order, order_task: OrderTask):
        self.order = order
        self.order_task = order_task

    @property
    def current_log(self) -> OrderTaskLog | None:
        return (
            OrderTaskLog.objects
            .filter(order=self.order, order_task=self.order_task)
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
            return True  # initial assignment
        return new_status in self.allowed_transitions()

    @transaction.atomic
    def transition_to(self, new_status: str, user: User, context: TaskTransitionContext | None = None, notes: str | None = None) -> OrderTaskLog:
        context = context or TaskTransitionContext(user=user, order=self.order, source="user")

        if self.current_status in self.TERMINAL_STATUSES:
            raise InvalidTaskTransitionError(
                f"Task already terminal ({self.current_status})"
            )

        if self.current_status and not self.can_transition_to(new_status):
            raise InvalidTaskTransitionError(
                f"Cannot transition task from '{self.current_status}' to '{new_status}'"
            )

        status = OrderTaskStatus.objects.get(status=new_status)

        log = OrderTaskLog.objects.create(
            order=self.order,
            order_task=self.order_task,
            order_task_status=status,
            assigned_to=user,
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

    def _on_assigned(self, context): pass
    def _on_in_progress(self, context): pass
    def _on_completed(self, context): pass
    def _on_unable_to_complete(self, context): pass
    
    @transaction.atomic
    def create_task(self, user: User, context: TaskTransitionContext | None = None, notes: str | None = None):
        context = context or TaskTransitionContext(
            user=user,
            order=self.order,
            source="system",
        )

        if self.current_status:
            raise InvalidTaskTransitionError(
                f"Task already created with status '{self.current_status}'"
            )

        status = OrderTaskStatus.objects.get(status=OrderTaskStatusChoices.ASSIGNED)

        OrderTaskLog.objects.create(
            order=self.order,
            order_task=self.order_task,
            order_task_status=status,
            assigned_to=user,
            notes=notes,
        )

        return self.transition_to(
            OrderTaskStatusChoices.ASSIGNED,
            user=user,
            context=context,
            notes=notes,
        )
    
    def complete_task(self, user: User, context: TaskTransitionContext | None = None, notes: str | None = None) -> OrderTaskLog:
        return self.transition_to(
            OrderTaskStatusChoices.COMPLETED,
            user=user,
            context=context,
            notes=notes,
        )