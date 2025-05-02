from abc import ABC, abstractmethod

from django.utils import timezone

import openai
from website import settings
from .models import LeadNote

class AIAgentServiceInterface(ABC):
    @abstractmethod
    def summarize_phone_call(self, lead_id: int, user_id: int, transcription_text: str) -> None:
        """
        Generate a structured summary of the given phone call based on its transcription
        and persist it as a lead note in the database.
        """
        pass

class OpenAIAgentService(AIAgentServiceInterface):
    def __init__(self, api_key: str):
        openai.api_key = api_key

    def summarize_phone_call(self, lead_id: int, user_id: int, transcription_text: str) -> None:
        prompt = f"""
            Take the example below:
            <p>
            <b>Caller:</b> Angie<br>
            <b>Call Purpose:</b> Inquiry about bartending services for a graduation party on May 4th<br><br>
            <b>Key Details:</b><br>
            - Angie is planning a small family and friends gathering in her backyard.<br>
            - She is interested in a bartending service and a bar setup (white or black rectangular bar).<br>
            - She has been following YD Cocktails for a month and loves their work.<br>
            - Wants to know pricing and drink options, including whether she needs to provide alcohol or if it can be included.<br>
            - Expressed interest in a surprise setup for her daughter, who loves espresso martinis.<br>
            - Curious about garnishes and decorations (e.g., espresso beans, orange slices, flowers) and whether YD Cocktails provides them.<br>
            - Prefers minimal effort on her end and is open to packages where everything is included.<br>
            - Considering a 3-hour bartending service from 3 PM to 6 PM.<br>
            - Wants a mix of specialty drinks (around 3-4) along with beer and wine.<br>
            - Confirmed drinks of interest: Espresso Martini, Mojito, Tequila Sunrise, and potentially Margarita or Sex on the Beach.<br>
            - Asked for a quote with different package options, including pricing for full-service vs. providing alcohol herself.<br>
            - Provided her email (AngieH10@aol.com) to receive the quote.<br><br> <b>Next Steps:</b><br>
            - Send Angie a quote with package options and pricing.<br>
            - Include recommendations for 3-4 specialty cocktails with garnish details.<br>
            - Suggest whether it’s more cost-effective for her to provide alcohol or opt for full service.<br>
            - Follow up to see if she wants to proceed with booking.<br>
            </p>

            The following transcript was a sales call for a bartending service. Summarize the key points in the following text while following the example above: {transcription_text}
        """
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes sales calls for CRM notes."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7,
            )
            summary = response.choices[0].message.content.strip()

            LeadNote.objects.create(
                note=summary,
                lead_id=lead_id,
                date_added=timezone.now(),
                added_by_user_id=user_id,
            )

        except Exception as e:
            raise RuntimeError(f"Failed to summarize phone call: {e}")

class AIAgentServiceFactory:
    @staticmethod
    def get_service() -> AIAgentServiceInterface:
        if settings.DEBUG:
            return AIAgentServiceFactory._create_openai_agent()
        return AIAgentServiceFactory._create_openai_agent()

    @staticmethod
    def _create_openai_agent() -> OpenAIAgentService:
        return OpenAIAgentService(api_key=settings.OPENAI_API_KEY)

class AIAgent(AIAgentServiceInterface):
    def __init__(self):
        self.service = AIAgentServiceFactory.get_service()

    def summarize_phone_call(self, lead_id: int, user_id: int, transcription_text: str) -> None:
        return self.service.summarize_phone_call(lead_id=lead_id, user_id=user_id, transcription_text=transcription_text)