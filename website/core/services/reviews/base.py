from abc import ABC, abstractmethod

class ReviewsServiceInterface(ABC):
    @abstractmethod
    def sync_reviews(self, lead):
        pass