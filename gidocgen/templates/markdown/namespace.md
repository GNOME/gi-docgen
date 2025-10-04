# {{ namespace.name }} {{ namespace.version }}

{% if CONFIG.description %}
{{ CONFIG.description }}
{% endif %}

## Overview

This is the API reference for {{ namespace.name }} {{ namespace.version }}.

{% if symbols.classes %}
## Classes

{% for class in symbols.classes %}
- [{{ class.name }}](class.{{ class.name }}.md) - {{ class.summary }}
{% endfor %}
{% endif %}

{% if symbols.interfaces %}
## Interfaces

{% for interface in symbols.interfaces %}
- [{{ interface.name }}](interface.{{ interface.name }}.md) - {{ interface.summary }}
{% endfor %}
{% endif %}

{% if symbols.structs %}
## Structs

{% for struct in symbols.structs %}
- [{{ struct.name }}](struct.{{ struct.name }}.md) - {{ struct.summary }}
{% endfor %}
{% endif %}

{% if symbols.unions %}
## Unions

{% for union in symbols.unions %}
- [{{ union.name }}](union.{{ union.name }}.md) - {{ union.summary }}
{% endfor %}
{% endif %}

{% if symbols.aliases %}
## Aliases

{% for alias in symbols.aliases %}
- [{{ alias.name }}](alias.{{ alias.name }}.md) - {{ alias.summary }}
{% endfor %}
{% endif %}

{% if symbols.enums %}
## Enumerations

{% for enum in symbols.enums %}
- [{{ enum.name }}](enum.{{ enum.name }}.md) - {{ enum.summary }}
{% endfor %}
{% endif %}

{% if symbols.bitfields %}
## Bitfields

{% for bitfield in symbols.bitfields %}
- [{{ bitfield.name }}](flags.{{ bitfield.name }}.md) - {{ bitfield.summary }}
{% endfor %}
{% endif %}

{% if symbols.domains %}
## Error Domains

{% for domain in symbols.domains %}
- [{{ domain.name }}](error.{{ domain.name }}.md) - {{ domain.summary }}
{% endfor %}
{% endif %}

{% if symbols.callbacks %}
## Callbacks

{% for callback in symbols.callbacks %}
- [{{ callback.name }}](callback.{{ callback.name }}.md) - {{ callback.summary }}
{% endfor %}
{% endif %}

{% if symbols.functions %}
## Functions

{% for function in symbols.functions %}
- [{{ function.name }}](func.{{ function.name }}.md) - {{ function.summary }}
{% endfor %}
{% endif %}

{% if symbols.function_macros %}
## Function Macros

{% for macro in symbols.function_macros %}
- [{{ macro.name }}](func.{{ macro.name }}.md) - {{ macro.summary }}
{% endfor %}
{% endif %}

{% if symbols.constants %}
## Constants

{% for constant in symbols.constants %}
- [{{ constant.name }}](const.{{ constant.name }}.md) - {{ constant.summary }}
{% endfor %}
{% endif %}

{% if CONFIG.dependencies|length > 0 %}
## Dependencies

{% for ns_name, repo in repository.includes.items() %}
{% for _, lib in CONFIG.dependencies.items() if lib.name == repo.namespace.name %}
- [{{ lib.name }}]({{ lib.docs_url }}) - {{ lib.description }}
{% endfor %}
{% endfor %}
{% endif %}