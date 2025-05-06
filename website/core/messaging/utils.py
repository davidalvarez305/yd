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