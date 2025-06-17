import logging
from core.models import InternalLog

class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        try:
            log = InternalLog(
                level=record.levelname,
                message=record.getMessage(),
                logger=record.name,
                pathname=record.pathname,
                lineno=record.lineno,
                exception=self.formatException(record.exc_info) if record.exc_info else None,
            )
            log.save()
        except Exception:
            pass