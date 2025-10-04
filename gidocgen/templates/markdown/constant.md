# {{ namespace.name }}.{{ constant.name }}

{% if CONFIG.is_unstable(constant.available_since) %}
**⚠️ Unstable** - This constant will be available in the next stable release
{% endif %}
{% if constant.deprecated_since %}
**⚠️ Deprecated** since {{ constant.deprecated_since.version }}: {{ constant.deprecated_since.message }}
{% endif %}

## Description

{{ constant.description }}

## Value

```
{{ constant.value }}
```

{% if constant.available_since %}
**Since:** {{ constant.available_since }}
{% endif %}