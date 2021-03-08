=====================
Linking items by name
=====================

Gi-docgen is capable of linking symbols across the same introspected namespace,
by using a qualifier fragment and the symbol name.

For instance:

::

    /**
     * ExampleFoo:
     *
     * This structure is related to [struct@Bar].
     */

    /**
     * example_foo_set_bar:
     *
     * Sets [struct@Example.Bar] on an instance of `Foo`.
     */

    /**
     * ExampleFoo:bar:
     *
     * Sets an instance of [`Bar`](struct.Bar.html) on `Foo`.
     */

will all link to ``Bar``.

Backticks will be stripped, so ``[`class@Foo`]`` will correctly link to ``Foo``.

The link can either be a fully qualified name, which includes the namespace; or
a name relative to the current names; for instance, both of the following links
will point to ``ExampleFoo`` when generating the documentation for the "Example"
namespace:

- ``[class@Foo]``
- ``[class@Example.Foo]``

The available qualifier fragments are:

+------------+-----------------------------+---------------------------------------------+
| Fragment   | Description                 | Example                                     |
+============+=============================+=============================================+
| `alias`    | An alias to another type    | ``[alias@Allocation]``                      |
+------------+-----------------------------+---------------------------------------------+
| `class`    | A ``GObject`` class         | ``[class@Widget]``, ``[class@Gdk.Surface]`` |
+------------+-----------------------------+---------------------------------------------+
| `const`    | A constant symbol           | ``[const@Gdk.KEY_q]``                       |
+------------+-----------------------------+---------------------------------------------+
| `ctor`     | A constructor function      | ``[ctor@Gtk.Box.new]``                      |
+------------+-----------------------------+---------------------------------------------+
| `enum`     | An enumeration              | ``[enum@Orientation]``                      |
+------------+-----------------------------+---------------------------------------------+
| `error`    | A ``GError`` domain         | ``[error@Gtk.BuilderParseError]``           |
+------------+-----------------------------+---------------------------------------------+
| `flags`    | A bitfield                  | ``[flags@Gdk.ModifierType]``                |
+------------+-----------------------------+---------------------------------------------+
| `func`     | A global or type function   | ``[func@Gtk.init]``, ``[func@show_uri]``,   |
|            |                             | ``[func@Gtk.Window.list_toplevels]``        |
+------------+-----------------------------+---------------------------------------------+
| `iface`    | A ``GTypeInterface``        | ``[iface@Gtk.Buildable]``                   |
+------------+-----------------------------+---------------------------------------------+
| `method`   | An instance or class method | ``[method@Gtk.Widget.show]``,               |
|            |                             | ``[method@WidgetClass.add_binding]``        |
+------------+-----------------------------+---------------------------------------------+
| `property` | A ``GObject`` property      | ``[property@Gtk.Orientable:orientation]``   |
+------------+-----------------------------+---------------------------------------------+
| `signal`   | A ``GObject`` signal        | ``[signal@Gtk.RecentManager::changed]``     |
+------------+-----------------------------+---------------------------------------------+
| `struct`   | A C structure or union      | ``[struct@Gtk.TextIter]``                   |
+------------+-----------------------------+---------------------------------------------+
| `vfunc`    | A virtual function          | ``[vfunc@Gtk.Widget.measure]``              |
+------------+-----------------------------+---------------------------------------------+

Additionally, the ``id`` fragment, followed by a C symbol identifier, will try to link to the function; for instance:

::

    // Equivalent to [func@Gtk.show_uri], will link to gtk_show_uri()
    [id@gtk_show_uri]

    // Equivalent to [method@Gtk.Widget.show], will link to gtk_widget_show()
    [id@gtk_widget_show]

The ``id`` fragment can only be used for symbols within the current namespace.

It's important to note that the ``method`` and ``func`` fragments can have
multiple meanings:

- the ``method`` fragment will match both instance and class methods, depending
  on the type used; for instance, to match an instance method you should use the
  type name, and to match a class method you should use the class name. The class
  method should not be confused with the ``vfunc`` fragment, which uses the type
  name and links to virtual methods defined in the class or interface structure.
  Class methods take the class pointer as their first argument, whereas virtual
  methods take the instance pointer as their first argument.

::

    // will link to gtk_widget_show()
    [method@Gtk.Widget.show]

    // will link to gtk_widget_class_add_binding()
    [method@Gtk.WidgetClass.add_binding]

    // will link to GtkWidgetClass.show
    [vfunc@Gtk.Widget.show]


- similarly, the ``func`` fragment will match global functions and type
  functions, depending on whether the link contains a type or not. Additionally,
  ``func`` will match function macros, which are part of the global namespace.

::

    // will link to gtk_show_uri()
    [func@Gtk.show_uri]

    // will link to gtk_window_list_toplevels()
    [func@Gtk.Window.list_toplevels]

    // will link to gtk_widget_class_bind_template_child()
    [func@Gtk.widget_class_bind_template_child]
