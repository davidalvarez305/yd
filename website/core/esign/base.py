from abc import ABC, abstractmethod

class ESignatureServiceInterface(ABC):
    
    @abstractmethod
    def handle_esign_completed(self, request):
        pass