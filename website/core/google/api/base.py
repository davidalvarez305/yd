from abc import ABC, abstractmethod

class GoogleAPIServiceInterface(ABC):
    @abstractmethod
    def get_sheets_data(self, lead):
        pass

    @abstractmethod
    def sync_reviews(self):
        pass