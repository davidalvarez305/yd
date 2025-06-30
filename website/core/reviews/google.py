from core.reviews.base import ReviewsServiceInterface
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from core.models import GoogleReview
from django.utils.dateparse import parse_datetime

class GoogleReviewsService(ReviewsServiceInterface):
    def __init__(self, access_token: str, account_id: str, location_id: str):
        self.access_token = access_token
        self.account_id = account_id
        self.location_id = location_id
        self.service = build("mybusiness", "v4", credentials=Credentials(token=access_token))

    def sync_reviews(self):
        request_params = {
            "parent": f"accounts/{self.account_id}/locations/{self.location_id}"
        }

        while True:
            request = self.service.accounts().locations().reviews().list(**request_params).execute()
            reviews = request.get("reviews", [])

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

            next_page_token = request.get("nextPageToken")
            if not next_page_token:
                break

            request_params["pageToken"] = next_page_token
    
    def _review_has_changes(self, instance: GoogleReview, values: dict):
        return any(
            getattr(instance, field) != value
            for field, value in values.items()
        )