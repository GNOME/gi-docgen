# {{ namespace.name }}.{{ class.name }}.{{ method.name }}

{% if CONFIG.is_unstable(method.available_since) %}
**⚠️ Unstable** - This method will be available in the next stable release
{% endif %}
{% if method.deprecated_since %}
**⚠️ Deprecated** since {{ method.deprecated_since.version }}: {{ method.deprecated_since.message }}
{% endif %}

## Description

{{ method.description }}

## Signature

```
{{ method.identifier }}
```

{% if method.arguments %}
## Parameters

{% for param in method.arguments %}
- `{{ param.name }}` ({{ param.type_name }}): {{ param.description }}
{% endfor %}
{% endif %}

{% if method.return_value %}
## Returns

{{ method.return_value.type_name }}: {{ method.return_value.description }}
{% endif %}

{% if method.available_since %}
**Since:** {{ method.available_since }}
{% endif %}