# {{ namespace.name }}.{{ enum.name }}

{% if CONFIG.is_unstable(enum.available_since) %}
**⚠️ Unstable** - This enumeration will be available in the next stable release
{% endif %}
{% if enum.deprecated_since %}
**⚠️ Deprecated** since {{ enum.deprecated_since.version }}: {{ enum.deprecated_since.message }}
{% endif %}

## Description

{{ enum.description }}

## Values

{% for member in enum.members %}
### {{ member.name }}

{{ member.description }}

**Value:** `{{ member.value }}`

{% if member.available_since %}
**Since:** {{ member.available_since }}
{% endif %}
{% if member.deprecated_since %}
**Deprecated since:** {{ member.deprecated_since.version }}: {{ member.deprecated_since.message }}
{% endif %}

{% endfor %}

{% if enum.available_since %}
**Since:** {{ enum.available_since }}
{% endif %}