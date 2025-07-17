from abc import ABC, abstractmethod

class FacebookAPIServiceInterface(ABC):
    @abstractmethod
    def get_lead_data(self, lead):
        pass

    @abstractmethod
    def get_ig_followers(self):
        pass

    @abstractmethod
    def get_leadgen_forms(self):
        pass

    @abstractmethod
    def get_all_leads_for_form(self):
        pass

    @abstractmethod
    def _refresh_access_token(self):
        pass