import os
from openai import OpenAI
import traceback
from website import settings
from core.models import Lead, LeadNote, User
from .base import AIAgentServiceInterface

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY") or settings.OPEN_AI_API_KEY,
)

class OpenAIAgentService(AIAgentServiceInterface):
    def __init__(self):
        self.client = client

    def summarize_phone_call(self, transcription_text: str) -> str:
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

            The following transcript was a sales call for a bartending service. Summarize the key points in the following text while following the example above. Please return only the HTML: {transcription_text}
        """
        try:
            response = self.client.responses.create(
                model="gpt-4.1-nano",
                instructions="You are a helpful assistant that summarizes sales calls for CRM notes.",
                input=prompt,
            )

            return response.output_text.strip()

        except Exception as e:
            print("Exception occurred during summarizing phone call:")
            traceback.print_exc()
            raise RuntimeError(f"Failed to summarize phone call: {e}")
    
    def generate_response(self, prompt: str) -> str:
        try:
            response = self.client.responses.create(
                model="gpt-4.1-nano",
                instructions="You are a helpful assistant that helps answer client queries.",
                input=prompt,
            )
            return response.output_text.strip()

        except Exception as e:
            print("Exception occurred during response generation:")
            traceback.print_exc()
            raise RuntimeError(f"Failed to generate response: {e}")