from abc import ABC, abstractmethod

class CallingTrackingServiceInterface(ABC):
    
    @abstractmethod
    def handle_inbound_tracking_call(self, request):
        pass

    @abstractmethod
    def handle_inbound_tracking_message(self, request):
        pass