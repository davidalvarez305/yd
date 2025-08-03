from core.enums import AlertStatus
from core.utils import default_alert_handler

class AlertMixin:
    alert_handler = None

    def alert(self, request, message, status: AlertStatus, reswap=False):
        handler = self.alert_handler or default_alert_handler
        return handler(request=request, message=message, status=status, reswap=reswap)

class ContextResolverMixin:
    def __init__(self, context=None, context_resolver=None):
        self.context = context or {}
        self.context_resolver = context_resolver

    def resolve_context(self, base=None, extra=None, request=None):
        if self.context_resolver:
            return self.context_resolver(base=base, extra=extra, request=request)

        return self.build_context(base, extra, request)
    
    def resolve_value(self, value, base=None, request=None):
        if callable(value):
            return value(base, request)
        elif isinstance(value, dict):
            return {k: self.resolve_value(v, base, request) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve_value(v, base, request) for v in value]
        return value

    def build_context(self, base=None, extra=None, request=None):
        context = dict(self.context)  # default static context

        # Inject any additional context passed dynamically
        if extra:
            context.update(extra)

        # Dynamically resolve string-based placeholders (supports nested attr access)
        resolved_context = {}
        for key, value in context.items():
            if callable(value) or isinstance(value, (dict, list)):
                resolved_context[key] = self.resolve_value(value, base, request)
            elif isinstance(value, str) and "{" in value:
                try:
                    resolved_context[key] = value.format(**vars(base))
                except Exception:
                    resolved_context[key] = value
            else:
                resolved_context[key] = value

        if base is not None:
            resolved_context["base"] = base
        if request is not None:
            resolved_context["request"] = request

        return resolved_context