from abc import ABC, abstractmethod

class AIAgentServiceInterface(ABC):
    @abstractmethod
    def summarize_phone_call(self, transcription_text: str) -> str:
        """
        Generate a structured summary of the given phone call based on its transcription
        and persist it as a lead note in the database.
        """
        pass

    @abstractmethod
    def generate_response(self, prompt: str) -> str:
        """
        Given a prompt, generate the appropriate response to the client's message / inquiry.
        """
        pass