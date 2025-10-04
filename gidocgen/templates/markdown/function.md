# {{ namespace.name }}.{{ func.name }}

{% if CONFIG.is_unstable(func.available_since) %}
**⚠️ Unstable** - This function will be available in the next stable release
{% endif %}
{% if func.deprecated_since %}
**⚠️ Deprecated** since {{ func.deprecated_since.version }}: {{ func.deprecated_since.message }}
{% endif %}

## Description

{{ func.description }}

## Signature

```
{{ func.identifier }}
```

{% if func.arguments %}
## Parameters

{% for param in func.arguments %}
- `{{ param.name }}` ({{ param.type_name }}): {{ param.description }}
{% endfor %}
{% endif %}

{% if func.return_value %}
## Returns

{{ func.return_value.type_name }}: {{ func.return_value.description }}
{% endif %}

{% if func.available_since %}
**Since:** {{ func.available_since }}
{% endif %}