# {{ namespace.name }}.{{ struct.name }}

{% if CONFIG.is_unstable(struct.available_since) %}
**⚠️ Unstable** - This struct will be available in the next stable release
{% endif %}
{% if struct.deprecated_since %}
**⚠️ Deprecated** since {{ struct.deprecated_since.version }}: {{ struct.deprecated_since.message }}
{% endif %}

## Description

{{ struct.description }}

{% if struct.fields %}
## Fields

{% for field in struct.fields %}
### {{ field.name }}

{{ field.description }}

**Type:** {{ field.type_name }}

{% if field.available_since %}
**Since:** {{ field.available_since }}
{% endif %}
{% if field.deprecated_since %}
**Deprecated since:** {{ field.deprecated_since.version }}: {{ field.deprecated_since.message }}
{% endif %}

{% endfor %}
{% endif %}

{% if struct.methods %}
## Methods

{% for method in struct.methods %}
### {{ method.name }}

{{ method.description }}

**Signature:** `{{ method.identifier }}`

{% if method.arguments %}
**Parameters:**
{% for param in method.arguments %}
- `{{ param.name }}` ({{ param.type_name }}): {{ param.description }}
{% endfor %}
{% endif %}

{% if method.return_value %}
**Returns:** {{ method.return_value.type_name }}: {{ method.return_value.description }}
{% endif %}

{% if method.available_since %}
**Since:** {{ method.available_since }}
{% endif %}
{% if method.deprecated_since %}
**Deprecated since:** {{ method.deprecated_since.version }}: {{ method.deprecated_since.message }}
{% endif %}

{% endfor %}
{% endif %}

{% if struct.available_since %}
**Since:** {{ struct.available_since }}
{% endif %}