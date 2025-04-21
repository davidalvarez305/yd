def strip_country_code(phone_number):
    return phone_number[-10:] if phone_number else ''