from django.utils.dateparse import parse_datetime

from core.reviews.base import ReviewsServiceInterface
from core.models import GoogleReview
from core.google.api import google_api_service


class GoogleReviewsService(ReviewsServiceInterface):
    def __init__(self):
        self.client = google_api_service()

    def sync_reviews(self):
        while True:
            reviews = self.client.get_mybusiness_reviews()

            for review in reviews:
                external_id = review.get("reviewId")
                reviewer = review.get("reviewer", {})

                values = {
                    "external_id": external_id,
                    "reviewer_display_name": reviewer.get("displayName"),
                    "reviewer_profile_photo_url": reviewer.get("profilePhotoUrl"),
                    "star_rating": review.get("starRating"),
                    "comment": review.get("comment"),
                    "create_time": parse_datetime(review.get("createTime")),
                    "update_time": parse_datetime(review.get("updateTime")),
                    "location_id": self.location_id,
                }

                instance = GoogleReview.objects.filter(external_id=external_id).first()
                if not instance:
                    GoogleReview.objects.create(**values)
                elif self._review_has_changes(instance, values):
                    for field, value in values.items():
                        setattr(instance, field, value)
                    instance.save()

    def _review_has_changes(self, instance: GoogleReview, values: dict):
        return any(
            getattr(instance, field) != value
            for field, value in values.items()
        )