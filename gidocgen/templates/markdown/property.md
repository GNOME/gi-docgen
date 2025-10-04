# {{ namespace.name }}.{{ class.name }}:{{ property.name }}

{% if CONFIG.is_unstable(property.available_since) %}
**⚠️ Unstable** - This property will be available in the next stable release
{% endif %}
{% if property.deprecated_since %}
**⚠️ Deprecated** since {{ property.deprecated_since.version }}: {{ property.deprecated_since.message }}
{% endif %}

## Description

{{ property.description }}

## Type

{{ property.type_name }}

## Access

{% if property.readable and property.writable %}
Read/Write
{% elif property.readable %}
Read-only
{% elif property.writable %}
Write-only
{% endif %}

{% if property.available_since %}
**Since:** {{ property.available_since }}
{% endif %}