.. SPDX-FileCopyrightText: 2023 Emmanuele Bassi
..
.. SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

=======
Content
=======

Gi-docgen parses the content of docblocks from the introspection data as plain
Markdown, using the `Python-Markdown <https://python-markdown.github.io/>`_ module.

For more information on Markdown, please see `the syntax rules <https://daringfireball.net/projects/markdown/>`_.

Basic syntax
------------

These are the elements outlined in the original Markdown documentation.

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Element
     - Markdown Syntax
   * - Heading
     - | ``# H1``
       | ``## H2``
       | ``### H3``
   * - Bold
     - ``**bold text**``
   * - Italic
     - ``*italicized text*``
   * - Blockquote
     - ``> blockquote``
   * - Ordered list
     - | ``1. First item``
       | ``2. Second item``
       | ``3. Third item``
   * - Unordered list
     - | ``- First item``
       | ``- Second item``
       | ``- Third item``
   * - Code
     - `` `code` ``
   * - Horizontal rule
     - ``---``
   * - Link
     - ``[title](https://www.example.com)``
   * - Image
     - ``![alt text](image.jpg)``

Extensions
----------

These are extensions to the basic syntax that are supported by gi-docgen:

- `Definition Lists <https://python-markdown.github.io/extensions/definition_lists/>`_
- `Fenced Code Blocks <https://python-markdown.github.io/extensions/fenced_code_blocks/>`_
- `Tables <https://python-markdown.github.io/extensions/tables/>`_

Admonitions
~~~~~~~~~~~

Gi-docgen supports "admonitions": asides, like notes, tips, and warnings.

The syntax for admonitions is:

::

    ::: type "optional title within double quotes"
        Any number of other indented markdown elements.

        This is another paragraph within the admonition

        - This is a list
        - With two items


The ``type`` can be one of:

- ``note``
- ``important``
- ``warning``
- ``seealso``
- ``tip``
- ``hint``

If there is no title, each type of admonition will use a default title:

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Type
     - Title
   * - ``note``
     - Note
   * - ``important``
     - Important
   * - ``warning``
     - Warning
   * - ``seealso``
     - See also
   * - ``tip``
     - Tip
   * - ``hint``
     - Hint

In order to distinguish the content of an admonition block from content
following the admonition, you should add an empty line after the admonition,
e.g.

::

    ::: tip
        This is a tip.

        This is still a tip


    This paragraph is outside the tip.


GTK-Doc compatibility
~~~~~~~~~~~~~~~~~~~~~

Gi-docgen tries to facilitate porting an API reference from gtk-doc. It
automatically turns gtk-doc sigils into code fragments:

- ``%CONSTANT``
- ``#TypeName``
- ``#TypeName:property``
- ``#TypeName::signal``
- ``symbol_name()``

.. important::
   Gi-docgen does **not** turn gtk-doc sigils into links, as they lack the
   specificity to allow cross-linking.
