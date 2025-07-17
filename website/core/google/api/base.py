from abc import ABC, abstractmethod

class GoogleAPIServiceInterface(ABC):
    @abstractmethod
    def get_sheet_data(self, spreadsheet_id: str, range_name: str) -> list[dict]:
        pass

    @abstractmethod
    def append_sheet_data(self, spreadsheet_id: str, range_name: str, data: list[dict]) -> dict:
        pass

    @abstractmethod
    def sync_reviews(self):
        pass

    @abstractmethod
    def send_email(self, to: str, subject: str, body: str) -> None:
        pass