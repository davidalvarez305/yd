def strip_country_code(phone_number: str) -> str:
    """
    Removes the country code from a phone number.
    For example, '+14155552671' becomes '4155552671'.
    """
    if not phone_number:
        return ""
    
    if phone_number.startswith('+1') and len(phone_number) == 12:
        return phone_number[2:]
    elif phone_number.startswith('+'):
        number = phone_number[1:]
        if len(number) > 10:
            return number[-10:]
        return number
    return phone_number

MIME_EXTENSION_MAP = {
    "audio/amr": ".amr",
    "video/3gpp": ".3gp",
    "audio/3gpp": ".3gp",
    "audio/mpeg": ".mp3",
    "video/mp4": ".mp4",
    "audio/mp4": ".m4a",
    "audio/ogg": ".ogg",
}