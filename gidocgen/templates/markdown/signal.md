# {{ namespace.name }}.{{ class.name }}::{{ signal.name }}

{% if CONFIG.is_unstable(signal.available_since) %}
**⚠️ Unstable** - This signal will be available in the next stable release
{% endif %}
{% if signal.deprecated_since %}
**⚠️ Deprecated** since {{ signal.deprecated_since.version }}: {{ signal.deprecated_since.message }}
{% endif %}

## Description

{{ signal.description }}

## Signature

```
{{ signal.identifier }}
```

{% if signal.parameters %}
## Parameters

{% for param in signal.parameters %}
- `{{ param.name }}` ({{ param.type_name }}): {{ param.description }}
{% endfor %}
{% endif %}

{% if signal.available_since %}
**Since:** {{ signal.available_since }}
{% endif %}