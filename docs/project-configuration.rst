=====================
Project configuration
=====================

Projects using gi-docgen should provide their own configuration file to describe
how to generate their API reference.

The configuration file format uses `ToML <https://toml.io/en/>`__ to provide key
and value pairs that will be used by gi-docgen and, optionally, by the templates
themselves.

Project configuration takes precendence over gi-docgen's defaults, but can be
overridden by command line options, where applicable.

Standard sections and keys
--------------------------

The ``theme`` section
~~~~~~~~~~~~~~~~~~~~~

The ``theme`` section is used to define the theme being used by gi-docgen when
generating the API reference of a project.

The following keys are used, if found:

``templates_dir``
  The directory that contains the templates to be used by gi-docgen. The
  default directory is inside the gi-docgen module directory. This key
  can be overridden by the ``--templates-dir`` command line argument.

``name``
  The name of the template to use. The name is a sub-directory of the
  ``template_dir`` directory, and will be used to load the template's
  configuration file. This key can be overridden by the ``--theme-name``
  command line argument.

``show_index_summary``
  A boolean value that controls whether to show the summary of each
  symbol in the namespace index.

``show_class_hierarchy``
  A boolean value that controls whether to generate a class graph
  with the ancestors of a type, as well as the implemented interfaces.
  Requires the ``dot`` utility from `GraphViz <https://graphviz.org/>`__
  installed in the ``PATH``.

The ``extra`` section
~~~~~~~~~~~~~~~~~~~~~

The ``extra`` section is used to define additional content used when
generating the API reference of a project.

The following keys are used, if found:

``content_files``
  A list of tuples. The first element of the tuple is a Markdown
  file name, relative to the directory specified by the ``--content-dir``
  command line argument; the second element of the tuple is the
  title used for the link to the content file. When generating the
  API reference, gi-docgen will transform the Markdown file into
  an HTML one, using the same pre-processing filters applied to the
  documentation blocks found in the introspection data. The
  generated HTML files will be placed in the root directory of
  the namespace.

``content_images``
  A list of files, relative to the directory specified by the
  ``--content-dir`` command line argument. The files will be copied
  in the root directory of the namespace.
