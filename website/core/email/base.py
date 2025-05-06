class EmailServiceInterface:
    def __init__(self, client):
        self.client = client

    def send_email(self, to: str, subject: str, body: str) -> None:
        """Method to send an email. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement send_email method")