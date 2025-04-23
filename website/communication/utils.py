import uuid
import mimetypes

def strip_country_code(phone_number):
    return phone_number[-10:] if phone_number else ''
    
def create_generic_file_name(content_type: str) -> str:
    if not content_type:
        raise ValueError("No content type provided")
    
    if content_type == "audio/webm":
        extension = ".webm"
    else:
        extension = mimetypes.guess_extension(content_type) or ".bin"
    
    return f"{uuid.uuid4()}{extension}"
