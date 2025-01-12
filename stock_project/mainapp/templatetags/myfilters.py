from django import template
register = template.Library()
# Creating custom filter.
@register.filter
def get(mapping, key):
    # mapping is the dictionary, we want to parse the value from ,using the key
    return mapping.get(key, '')