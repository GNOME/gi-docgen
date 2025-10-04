# {{ namespace.name }}.{{ class.name }}.{{ vfunc.name }}

{% if CONFIG.is_unstable(vfunc.available_since) %}
**⚠️ Unstable** - This virtual function will be available in the next stable release
{% endif %}
{% if vfunc.deprecated_since %}
**⚠️ Deprecated** since {{ vfunc.deprecated_since.version }}: {{ vfunc.deprecated_since.message }}
{% endif %}

## Description

{{ vfunc.description }}

## Signature

```
{{ vfunc.identifier }}
```

{% if vfunc.arguments %}
## Parameters

{% for param in vfunc.arguments %}
- `{{ param.name }}` ({{ param.type_name }}): {{ param.description }}
{% endfor %}
{% endif %}

{% if vfunc.return_value %}
## Returns

{{ vfunc.return_value.type_name }}: {{ vfunc.return_value.description }}
{% endif %}

{% if vfunc.available_since %}
**Since:** {{ vfunc.available_since }}
{% endif %}