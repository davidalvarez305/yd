from abc import ABC, abstractmethod

class CallingServiceInterface(ABC):
    @abstractmethod
    def handle_inbound_call(self, request):
        pass