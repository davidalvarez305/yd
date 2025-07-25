from datetime import timedelta
import mimetypes
import os
import random
import re
from urllib.parse import parse_qs, urlparse
import uuid
from pathlib import Path
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware, is_naive

import requests

from django.db import models

from website import settings
from core.enums import AlertHTTPCodes, AlertStatus
from io import BytesIO
from moviepy import VideoFileClip

from pydub import AudioSegment
from core.messaging.utils import MIME_EXTENSION_MAP
from core.logger import logger

import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException

def format_phone_number(phone_number):
    if phone_number is None:
        raise TypeError('Phone number string cannot be NoneType')

    cleaned = re.sub(r'\D', '', phone_number)
    
    if len(cleaned) == 10:
        return f"({cleaned[:3]}) {cleaned[3:6]} - {cleaned[6:]}"
    
    return ""

def is_mobile(user_agent):

    if user_agent is None:
        raise TypeError('User-Agent string cannot be NoneType')

    return any(keyword in user_agent for keyword in ["Mobile", "Android", "iPhone", "iPad", "iPod"])

def create_generic_file_name(content_type: str, extension: str) -> str:
    if not content_type:
        raise ValidationError('No content type provided')

    if not extension:
        extension = mimetypes.guess_extension(content_type) or MIME_EXTENSION_MAP.get(content_type, '.bin')

    if "." not in extension:
        raise ValidationError('Extension must have a dot (e.g. ".mp3")')

    return str(uuid.uuid4()) + extension

def add_form_field_class(widget, new_classes):
    existing = widget.attrs.get('class', '')
    all_classes = set(existing.split() + new_classes.split())
    widget.attrs['class'] = ' '.join(sorted(all_classes))

def deep_getattr(obj, attr, default=None):
    try:
        for part in attr.split("."):
            obj = getattr(obj, part)
            if callable(obj) and not isinstance(obj, (models.Manager, models.QuerySet)):
                obj = obj()
    except AttributeError:
        return default
    return obj


def cleanup_dir_files(dir_path):
    directory = Path(dir_path)

    for file in directory.iterdir():
        if file.is_file():
            file.unlink()

def download_file_from_twilio(twilio_resource: str, local_file_path: str) -> None:
        try:
            response = requests.get(
                twilio_resource,
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                stream=True
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.exception(str(e), exc_info=True)
            raise Exception(f"Failed to download file: {e}")

        try:
            with open(local_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as e:
            logger.exception(str(e), exc_info=True)
            raise Exception(f"Failed to save file locally: {e}")

def format_phone_number(phone_number: str) -> str:
    """
    Format a 10-digit US phone number into (XXX) XXX - XXXX format.
    Returns the original string if not 10 digits.
    """
    digits = ''.join(filter(str.isdigit, phone_number))
    
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]} - {digits[6:]}"
    
    return phone_number

def get_first_field_error(form):
    """
    Returns the first field-specific error message from a Django form,
    excluding non-field (__all__) errors.

    Returns:
        str: The first error message, or empty string if none found.
    """
    for _, errors in form.errors.items():
        if getattr(errors, 'as_text', None):
            return errors.as_text()

    return ''

def media_upload_path(instance, filename):
    if instance.content_type.startswith("image/"):
        subdir = "images"
    elif instance.content_type.startswith("audio/"):
        subdir = "audio"
    elif instance.content_type.startswith("video/"):
        subdir = "videos"
    else:
        subdir = "other"

    return os.path.join("uploads", subdir, filename)

def save_image_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    return os.path.join('uploads/images/', f"{uuid.uuid4()}{ext}")

def format_text_message(text):
    final = ''

    for line in text.split("\n"):
        final += f"""
{line}
"""
    return final

def default_alert_handler(request, message, status: AlertStatus, reswap=False):
    template = 'core/success_alert.html' if status == AlertStatus.SUCCESS else 'core/error_alert.html'
    status_code = AlertHTTPCodes.get_http_code(status)

    response = render(request, template_name=template, context={'message': message}, status=status_code)
    if reswap:
        response['HX-Reswap'] = 'outerHTML'
        response['HX-Retarget'] = '#alertModal'
    return response

def get_average_ratings():
    from core.models import GoogleReview
    return GoogleReview.objects.aggregate(rating_value=models.Avg('rating_value'))['rating_value']


def get_paired_reviews(max_pairs=4):
    from core.models import GoogleReview
    long_reviews = []
    short_reviews = []

    reviews = GoogleReview.objects.filter(should_show=True)

    for review in reviews.order_by('-date_created'):
        if len(review.comment) > 200:
            long_reviews.append(review)
        elif len(review.comment) > 0:
            short_reviews.append(review)

        if len(long_reviews) >= max_pairs and len(short_reviews) >= max_pairs:
            break

    reviews = []
    for long, short in zip(long_reviews[:max_pairs], short_reviews[:max_pairs]):
        reviews.append((long, 2))   # long review with col-span-2
        reviews.append((short, 1))  # short review with col-span-1

    return reviews

class AttachmentProcessingError(Exception):
    pass

def convert_audio_format(file, target_file_path: str, to_format: str) -> BytesIO:
    try:
        with open(target_file_path, "wb") as tmp_file:
            if hasattr(file, "chunks"):
                for chunk in file.chunks():
                    tmp_file.write(chunk)
            else:
                tmp_file.write(file.read())

        audio = AudioSegment.from_file(target_file_path)
        buffer = BytesIO()
        audio.export(buffer, format=to_format, bitrate="192k")
        buffer.seek(0)
        return buffer

    except Exception as e:
        raise AttachmentProcessingError(f"Audio conversion failed: {str(e)}") from e

    finally:
        if os.path.exists(target_file_path):
            os.remove(target_file_path)

def convert_video_to_mp4(input_path: str, output_path: str):
    clip = VideoFileClip(input_path)
    clip.write_videofile(output_path, codec="libx264", audio_codec="aac", preset="medium", threads=2)
    clip.close()

def get_upload_sub_dir(content_type: str) -> str:
    return {
        "audio": "audio",
        "image": "images",
        "video": "videos",
    }.get(content_type.split("/")[0], "misc")

def seconds_to_minutes(duration: int) -> str:
    minutes = duration // 60
    seconds = duration % 60
    
    return f"{minutes} minute{'s' if minutes != 1 else ''} {seconds} second{'s' if seconds != 1 else ''}"

def get_facebook_token_expiry_date():
    return timezone.now() + timedelta(seconds=60 * 24 * 60 * 60)

def str_to_datetime(value):
    if isinstance(value, str):
        value = parse_datetime(value)
    if value and is_naive(value):
        value = make_aware(value)
    return value

def generate_random_long_int(num_digits=18):
    """
    Generate a random long integer with a given number of digits.
    Default: 18 digits (fits safely within a BigIntegerField).
    """
    if num_digits < 1:
        raise ValueError("num_digits must be >= 1")

    lower = 10**(num_digits - 1)
    upper = (10**num_digits) - 1
    return random.randint(lower, upper)

def normalize_phone_number(value: str, default_region: str = "US") -> str | None:
    """
    Normalizes a phone number to E.164 format (e.g., +17865122546).

    Args:
        value (str): Raw phone number string.
        default_region (str): Default region to assume (if no country code). Default is 'US'.

    Returns:
        str: Normalized E.164 phone number (e.g., +17865122546), or an empty string if invalid.
    """
    if not value or not isinstance(value, str):
        return ""

    try:
        number = phonenumbers.parse(value, default_region)
        if phonenumbers.is_valid_number(number):
            return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
    except NumberParseException as e:
        logger.exception(str(e), exc_info=True)
        pass

    return None

def extract_url_param_value(url: str, param: str) -> str:
    if not url or not param:
        return ""

    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    values = query_params.get(param)
    return values[0] if values else ""

def parse_money(value: str) -> float:
    """
    Convert a money string like "$100.00" or "USD 1,000.99" into a float.
    
    Returns 0.0 if the value is empty, None, or invalid.
    """
    if not value or not isinstance(value, str):
        return 0.0

    clean = re.sub(r'[^\d.,-]', '', value)

    if ',' in clean and clean.count(',') > clean.count('.'):
        clean = clean.replace(',', '')

    try:
        return float(clean)
    except ValueError:
        return 0.0