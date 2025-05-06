from abc import ABC, abstractmethod

class MessagingServiceInterface(ABC):
    @abstractmethod
    def handle_inbound_message(self, request):
        pass

    @abstractmethod
    def handle_outbound_message(self, form):
        pass

    @abstractmethod
    def _send_text_message(self, message):
        pass