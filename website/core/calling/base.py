from abc import ABC, abstractmethod

class CallingServiceInterface(ABC):
    @abstractmethod
    def handle_inbound_call(self, request):
        pass

    @abstractmethod
    def handle_call_status_callback(self, request):
        pass

    @abstractmethod
    def handle_call_recording_callback(self, request, transcription_service, ai_agent):
        pass