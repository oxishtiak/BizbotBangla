from django import template


register = template.Library()


_DIGIT_MAP = str.maketrans('0123456789.-', '০১২৩৪৫৬৭৮৯.-')


@register.filter(name='bn')
def bangla_number(value):
    return str(value).translate(_DIGIT_MAP)
