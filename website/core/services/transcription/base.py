from abc import ABC, abstractmethod

class TranscriptionServiceInterface(ABC):
    @abstractmethod
    def transcribe_audio(self, uri: str) -> dict:
        """Transcribe from given uri and return dict."""
        pass