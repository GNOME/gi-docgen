# {{ namespace.name }}.{{ class.name }}.{{ class_method.name }}

{% if CONFIG.is_unstable(class_method.available_since) %}
**⚠️ Unstable** - This class method will be available in the next stable release
{% endif %}
{% if class_method.deprecated_since %}
**⚠️ Deprecated** since {{ class_method.deprecated_since.version }}: {{ class_method.deprecated_since.message }}
{% endif %}

## Description

{{ class_method.description }}

## Signature

```
{{ class_method.identifier }}
```

{% if class_method.arguments %}
## Parameters

{% for param in class_method.arguments %}
- `{{ param.name }}` ({{ param.type_name }}): {{ param.description }}
{% endfor %}
{% endif %}

{% if class_method.return_value %}
## Returns

{{ class_method.return_value.type_name }}: {{ class_method.return_value.description }}
{% endif %}

{% if class_method.available_since %}
**Since:** {{ class_method.available_since }}
{% endif %}