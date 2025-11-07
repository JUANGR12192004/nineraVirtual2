from django import template

register = template.Library()


def _clone_attrs(field):
    return field.field.widget.attrs.copy()


@register.filter(name='field_attrs')
def field_attrs(field, arg):
    attrs = _clone_attrs(field)
    if arg:
        for chunk in str(arg).split(','):
            if not chunk:
                continue
            if '=' in chunk:
                key, value = chunk.split('=', 1)
            elif ':' in chunk:
                key, value = chunk.split(':', 1)
            else:
                key, value = chunk, ''
            key = key.strip()
            value = value.strip()
            if key:
                if key == 'class' and attrs.get('class'):
                    attrs['class'] = f"{attrs['class']} {value}".strip()
                else:
                    attrs[key] = value
    return field.as_widget(attrs=attrs)
