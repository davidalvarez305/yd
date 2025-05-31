import json
import hmac
import hashlib

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.db import transaction

from core.models import Lead, LeadMarketing, LeadStatusEnum, MarketingCampaign
from marketing.enums import ConversionServiceType
from website import settings
from marketing.utils import facebook_lead_retrieval

@csrf_exempt
def handle_facebook_create_new_lead(request: HttpRequest) -> HttpResponse:
    try:
        if request.method == 'GET':
            verify_token = request.GET.dict().get('hub.verify_token')
            challenge = request.GET.dict().get('hub.challenge')
            internal_verify_token = settings.FACEBOOK_APP_VERIFY_TOKEN

            if not internal_verify_token == verify_token:
                return HttpResponse('Unauthorized', status=401)

            return HttpResponse(challenge, status=200)

        elif request.method == 'POST':
            app_secret = settings.FACEBOOK_APP_SECRET
            signature_header = request.headers.get('X-Hub-Signature-256')

            if not signature_header:
                return HttpResponse('Missing signature', status=400)

            received_signature = signature_header.split('sha256=')[1]
            expected_signature = hmac.new(
                key=app_secret.encode('utf-8'),
                msg=request.body,
                digestmod=hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(received_signature, expected_signature):
                return HttpResponse('Invalid signature', status=403)

            payload = json.loads(request.body)
            entries = []

            for entry in payload.get('entry', []):
                for change in entry.get('changes', []):
                    if change.get('field') == 'leadgen':
                        value = change.get('value', {})
                        entries.append({
                            'leadgen_id': value.get('leadgen_id'),
                            'page_id': value.get('page_id'),
                            'form_id': value.get('form_id'),
                            'adgroup_id': value.get('adgroup_id'),
                            'ad_id': value.get('ad_id'),
                            'created_time': value.get('created_time'),
                        })

            for entry in entries:
                data = facebook_lead_retrieval(entry)

                with transaction.atomic():
                    lead, created = Lead.objects.get_or_create(
                        phone_number=data.get('phone_number'),
                        defaults={
                            'email': data.get('email'),
                            'full_name': data.get('full_name'),
                        }
                    )

                    if created:
                        marketing, _ = LeadMarketing.objects.get_or_create(
                            instant_form_lead_id=entry.get('leadgen_id'),
                            defaults={
                                'lead': lead,
                                'source': data.get('platform'),
                                'medium': 'paid',
                                'channel': 'social',
                                'instant_form_id': data.get('form_id'),
                            }
                        )

                        if not data.get('is_organic'):
                            campaign, _ = MarketingCampaign.objects.get_or_create(
                                marketing_campaign_id=data.get('campaign_id'),
                                defaults={
                                    'name': data.get('campaign_name'),
                                    'platform_id': ConversionServiceType.FACEBOOK.value,
                                }
                            )
                            marketing.marketing_campaign = campaign
                            marketing.save()

                        lead.change_lead_status(status=LeadStatusEnum.LEAD_CREATED)
                    elif lead.is_inactive():
                        lead.change_lead_status(status=LeadStatusEnum.RE_ENGAGED)

            return JsonResponse({'status': 'received'}, status=200)

        else:
            return HttpResponse(status=405)

    except Exception as e:
        print(f'Error: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)