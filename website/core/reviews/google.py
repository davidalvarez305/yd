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
        request = self.service.accounts().locations().reviews().list(parent=f"accounts/{self.account_id}/locations/{self.location_id}").execute()
        reviews = request.get("reviews", [])

        for review in reviews:
            external_id = review.get("reviewId")

            reviewer = review.get("reviewer", {})
            display_name = reviewer.get("displayName")
            profile_photo_url = reviewer.get("profilePhotoUrl")

            comment = review.get("comment")
            star_rating = review.get("starRating")
            create_time = parse_datetime(review.get("createTime"))
            update_time = parse_datetime(review.get("updateTime"))

            values = {
                "external_id": external_id,
                "reviewer_display_name": display_name,
                "reviewer_profile_photo_url": profile_photo_url,
                "star_rating": star_rating,
                "comment": comment,
                "create_time": create_time,
                "update_time": update_time,
                "location_id": self.location_id,
            }

            instance = GoogleReview.objects.filter(external_id=external_id).first()
            if not instance:
                GoogleReview.objects.create(**values)
            elif self._review_has_changes(instance=instance, values=values):
                for field, value in values.items():
                    setattr(instance, field, value)
                instance.save()
    
    def _review_has_changes(self, instance: GoogleReview, values: dict):
        return any(
            getattr(instance, field) != value
            for field, value in values.items()
        )