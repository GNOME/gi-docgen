# {{ namespace.name }}.{{ class.name }}.{{ type_func.name }}

{% if CONFIG.is_unstable(type_func.available_since) %}
**⚠️ Unstable** - This constructor will be available in the next stable release
{% endif %}
{% if type_func.deprecated_since %}
**⚠️ Deprecated** since {{ type_func.deprecated_since.version }}: {{ type_func.deprecated_since.message }}
{% endif %}

## Description

{{ type_func.description }}

## Signature

```
{{ type_func.identifier }}
```

{% if type_func.arguments %}
## Parameters

{% for param in type_func.arguments %}
- `{{ param.name }}` ({{ param.type_name }}): {{ param.description }}
{% endfor %}
{% endif %}

{% if type_func.return_value %}
## Returns

{{ type_func.return_value.type_name }}: {{ type_func.return_value.description }}
{% endif %}

{% if type_func.available_since %}
**Since:** {{ type_func.available_since }}
{% endif %}