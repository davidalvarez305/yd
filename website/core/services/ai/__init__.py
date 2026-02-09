from django.utils.functional import LazyObject
from django.utils.module_loading import import_string
from website import settings

class AIAgentService(LazyObject):
    def _setup(self):
        cls = import_string(settings.AI_AGENT_SERVICE)
        self._wrapped = cls()

ai_agent = AIAgentService()