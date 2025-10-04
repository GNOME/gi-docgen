# {{ namespace.name }}.{{ class.name }}

{% if CONFIG.is_unstable(class.available_since) %}
**⚠️ Unstable** - This type will be available in the next stable release
{% endif %}
{% if class.deprecated_since %}
**⚠️ Deprecated** since {{ class.deprecated_since.version }}: {{ class.deprecated_since.message }}
{% endif %}

## Description

{{ class.description }}

{% if CONFIG.show_class_hierarchy and (class.ancestors or class.interfaces) %}
## Hierarchy

{% if class.ancestors %}
**Ancestors:**
{% for ancestor in class.ancestors %}
- {{ ancestor.name }}
{% endfor %}
{% endif %}

{% if class.interfaces %}
**Implements:**
{% for interface in class.interfaces %}
- {{ interface.name }}
{% endfor %}
{% endif %}
{% endif %}

{% if class.ctors %}
## Constructors

{% for ctor in class.ctors %}
### {{ ctor.name }}

{{ ctor.summary }}

**Signature:** `{{ ctor.identifier }}`

{% if ctor.arguments %}
**Parameters:**
{% for param in ctor.arguments %}
- `{{ param.name }}` ({{ param.type_name }}): {{ param.description }}
{% endfor %}
{% endif %}

{% if ctor.available_since %}
**Since:** {{ ctor.available_since }}
{% endif %}
{% if ctor.deprecated_since %}
**Deprecated since:** {{ ctor.deprecated_since.version }}: {{ ctor.deprecated_since.message }}
{% endif %}

{% endfor %}
{% endif %}

{% if class.type_funcs %}
## Functions

{% for func in class.type_funcs %}
### {{ func.name }}

{{ func.summary }}

**Signature:** `{{ func.identifier }}`

{% if func.arguments %}
**Parameters:**
{% for param in func.arguments %}
- `{{ param.name }}` ({{ param.type_name }}): {{ param.description }}
{% endfor %}
{% endif %}

{% if func.return_value %}
**Returns:** {{ func.return_value.type_name }}: {{ func.return_value.description }}
{% endif %}

{% if func.available_since %}
**Since:** {{ func.available_since }}
{% endif %}
{% if func.deprecated_since %}
**Deprecated since:** {{ func.deprecated_since.version }}: {{ func.deprecated_since.message }}
{% endif %}

{% endfor %}
{% endif %}

{% if class.methods %}
## Methods

{% for method in class.methods %}
### {{ method.name }}

{{ method.summary }}

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

{% if class.properties %}
## Properties

{% for prop in class.properties %}
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

{% if class.signals %}
## Signals

{% for signal in class.signals %}
### {{ signal.name }}

{{ signal.summary }}

**Signature:** `{{ signal.identifier }}`

{% if signal.arguments %}
**Parameters:**
{% for param in signal.arguments %}
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

{% if class.class_methods %}
## Class Methods

{% for method in class.class_methods %}
### {{ method.name }}

{{ method.summary }}

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

{% if class.virtual_methods %}
## Virtual Methods

{% for method in class.virtual_methods %}
### {{ method.name }}

{{ method.summary }}

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