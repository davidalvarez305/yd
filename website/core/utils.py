import re
import uuid
import mimetypes

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

    
def create_generic_file_name(content_type: str) -> str:
    if not content_type:
        raise ValueError("No content type provided")
    
    if content_type == "audio/webm":
        extension = ".webm"
    else:
        extension = mimetypes.guess_extension(content_type) or ".bin"
    
    return f"{uuid.uuid4()}{extension}"

def add_form_field_class(widget, new_classes):
    existing = widget.attrs.get('class', '')
    all_classes = set(existing.split() + new_classes.split())
    widget.attrs['class'] = ' '.join(sorted(all_classes))

def deep_getattr(obj, path):
    attrs = path.split(".")
    for attr in attrs:
        obj = getattr(obj, attr, None)
        if callable(obj):
            obj = obj()
        if obj is None:
            break
    return obj
