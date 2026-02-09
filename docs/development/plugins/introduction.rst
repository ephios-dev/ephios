Introduction
============

ephios is designed to be flexible and extensible. This means that you can hook into several parts of the system with a plugin and change or add functionality.
We are sending out several Django signals that you can register for. You can check out the list of :doc:`signals`.
For some signals, you need to return subclasses of our :doc:`classes`


Creating a plugin
-----------------
In general, an ephios plugin is a python package with a special entrypoint.
To save you the hassle, we are providing a cookiecutter template with everything prepared for you to start.

To get started, make sure that you have at least Python 3.10 and cookiecutter installed
with ``pip install cookiecutter``

You can create your project by executing
``cookiecutter https://github.com/ephios-dev/ephios-plugin-template``.
Make sure to use a valid python package name (only letters, numbers and underscores)
as your app name. Change to the newly created folder and make sure to follow the
setup steps metioned in :doc:`/development/contributing/` but prefixed by ``python -m ephios``
instead of ``python manage.py`` to setup your local ephios instance for testing.

You will find a (nearly) empty django app inside your project. This app will be
listed in INSTALLED_APPS of ephios, so you can use all common django features likes
migrations and URLs.
You should register to some of the :doc:`signals` to get called by ephios.
Please note that with instances of ``PluginSignal``, only activated plugins
will receive signal calls.

To further customize specify how your plugin is displayed and shown within ephios,
alter the attributes of the ``EphiosPluginMeta`` class found in your plugins ``apps.py``.
If you set ``visible`` to ``False`` the plugin will not show up in the ephios settings, so
admins wont be able to enable it. If you set ``force_enabled`` to ``True`` ephios will always
consider the plugin enabled. This only makes sense for invisible plugins.

Installing a plugin
-------------------
To package your plugin, you can run ``uv build`` which will produce a python wheel. You can either copy the wheel file
to your server and install it with ``pip install /path/to/build.whl`` or publish it to pypi using ``uv publish``. You need to create
an API token with pypi for that. Then you can install your plugin from pypi with ``pip install app_name``. Make sure to install the
plugin in the same virtual environment as ephios (if applicable). Please note that you need to activate the plugin from within ephios in order to see it.

.. toctree::
    :maxdepth: 0
