from django import template

register = template.Library()

@register.filter
def times(number):
    return range(int(number))

@register.filter
def stars(rating: float):
    stars = []

    decimal = rating % 1
    base = int(rating)

    if decimal >= 0.8:
        full_stars = base + 1
        half_star = False
    elif 0.3 <= decimal < 0.8:
        full_stars = base
        half_star = True
    else:
        full_stars = base
        half_star = False

    stars.extend([False] * full_stars)

    if half_star:
        stars.append(True)

    return stars