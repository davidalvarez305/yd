from abc import ABC, abstractmethod

class FacebookAPIServiceInterface(ABC):
    @abstractmethod
    def get_lead_data(self, lead):
        pass

    @abstractmethod
    def _refresh_access_token(self):
        pass