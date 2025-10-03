from abc import ABC, abstractmethod

class ESignatureServiceInterface(ABC):
    
    @abstractmethod
    def handle_agreement_signed(self, request):
        pass