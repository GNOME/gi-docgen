# {{ namespace.name }}.{{ interface.name }}

{% if CONFIG.is_unstable(interface.available_since) %}
**⚠️ Unstable** - This interface will be available in the next stable release
{% endif %}
{% if interface.deprecated_since %}
**⚠️ Deprecated** since {{ interface.deprecated_since.version }}: {{ interface.deprecated_since.message }}
{% endif %}

## Description

{{ interface.description }}

{% if interface.methods %}
## Methods

{% for method in interface.methods %}
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

{% if interface.properties %}
## Properties

{% for prop in interface.properties %}
### {{ prop.name }}

{{ prop.description }}

**Type:** {{ prop.type_name }}

{% if prop.readable and prop.writable %}
**Access:** Read/Write
{% elif prop.readable %}
**Access:** Read-only
{% elif prop.writable %}
**Access:** Write-only
{% endif %}

{% if prop.available_since %}
**Since:** {{ prop.available_since }}
{% endif %}
{% if prop.deprecated_since %}
**Deprecated since:** {{ prop.deprecated_since.version }}: {{ prop.deprecated_since.message }}
{% endif %}

{% endfor %}
{% endif %}

{% if interface.signals %}
## Signals

{% for signal in interface.signals %}
### {{ signal.name }}

{{ signal.description }}

**Signature:** `{{ signal.identifier }}`

{% if signal.parameters %}
**Parameters:**
{% for param in signal.parameters %}
- `{{ param.name }}` ({{ param.type_name }}): {{ param.description }}
{% endfor %}
{% endif %}

{% if signal.available_since %}
**Since:** {{ signal.available_since }}
{% endif %}
{% if signal.deprecated_since %}
**Deprecated since:** {{ signal.deprecated_since.version }}: {{ signal.deprecated_since.message }}
{% endif %}

{% endfor %}
{% endif %}

{% if interface.virtual_methods %}
## Virtual Methods

{% for method in interface.virtual_methods %}
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