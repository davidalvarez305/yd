import json
import hmac
import hashlib
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest, HttpResponse
from django.db import transaction

from core.models import InstantForm, Lead, LeadMarketing, LeadStatusEnum, MarketingCampaign
from marketing.enums import ConversionServiceType

@csrf_exempt
def handle_facebook_create_new_lead(request: HttpRequest) -> HttpResponse:
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    app_secret = settings.FACEBOOK_APP_SECRET
    signature_header = request.headers.get('X-Hub-Signature-256')

    if not signature_header:
        return HttpResponse('Missing signature', status=400)

    try:
        received_signature = signature_header.split('sha256=')[1]
    except IndexError:
        return HttpResponse('Malformed signature header', status=400)

    expected_signature = hmac.new(
        key=app_secret.encode('utf-8'),
        msg=request.body,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(received_signature, expected_signature):
        return HttpResponse('Invalid signature', status=403)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse('Invalid JSON', status=400)

    entries = []

    for entry in payload.get('entry', []):
        for change in entry.get('changes', []):
            if change.get('field') == 'leadgen':
                value = change.get('value', {})
                lead = {
                    'leadgen_id': value.get('leadgen_id'),
                    'page_id': value.get('page_id'),
                    'form_id': value.get('form_id'),
                    'adgroup_id': value.get('adgroup_id'),
                    'ad_id': value.get('ad_id'),
                    'created_time': value.get('created_time'),
                }
                entries.append(lead)

    print('Extracted Leads:', entries)

    for entry in entries:
        with transaction.atomic():
            lead, created = Lead.objects.update_or_create(
                phone_number=entry.get('phone_number'),
                defaults={
                    'email': entry.get('email'),
                    'full_name': entry.get('full_name'),
                }
            )

            instant_form, _ = InstantForm.objects.get_or_create(
                instant_form_id=entry.get('form_id'),
                defaults={
                    'name': entry.get('form_name')
                }
            )

            campaign, _ = MarketingCampaign.objects.get_or_create(
                marketing_campaign_id=entry.get('campaign_id'),
                defaults={
                    'name': entry.get('campaign_name'),
                    'platform_id': ConversionServiceType.FACEBOOK.value,
                }
            )

            if created:
                LeadMarketing.objects.create(
                    instant_form_lead_id=entry.get('leadgen_id'),
                    lead=lead,
                    source='fb',
                    medium='paid',
                    channel='social',
                    instant_form=instant_form,
                    marketing_campaign=campaign,
                )

                lead.change_lead_status(status=LeadStatusEnum.LEAD_CREATED)
            else:
                lead.change_lead_status(status=LeadStatusEnum.RE_ENGAGED)


    response = {'status': 'received', 'leads_count': len(entries)}
    return HttpResponse(json.dumps(response), content_type='application/json', status=200)