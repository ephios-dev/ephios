Contributing
============

Contributions to ephios are welcome. If you want to see what we are currently up to, check the available
`issues <https://github.com/ephios-dev/ephios/issues>`_.

If you have an idea for new feature you should start by deciding whether you want to write a plugin (see :doc:`plugin`)
or to contribute the feature to the ephios core code. A plugin is usually suitable if the feature is very specific to
a small set of users (e.g. a specific signup process only used in your local organisation) or the feature is not related
to the core tasks of ephios (e.g. a system for stock management). If all ephios users could profit from your feature,
you should consider contributing it to the core code. Please start by describing your feature in a new issue in the
GitHub repository to coordinate the extent with us.
When working on existing issues, please assign yourself and create a pull request early on.

Development setup
-----------------

To set up a development version on your local machine, you need to execute the following steps:

#. Check out the `repository <https://github.com/ephios-dev/ephios>`_ and cd to it
#. Set up a virtualenv for the project with Python >=3.8 and activate it
#. Install poetry (if not already installed): `Installation guide <https://python-poetry.org/docs/#installation>`_
#. Install dependencies with ``poetry install``
#. Create env file with ``cp .env.example .env``
#. Migrate the database with ``python manage.py migrate``
#. Compile translations with ``python manage.py compilemessages`` and ``python manage.py compilejsi18n``
#. Load data for testing with ``python manage.py setupdata debug``
#. Start the development server with ``python manage.py runserver``
#. Open your web browser, visit ``http://localhost:8000`` and log in with the default credentials (user ``admin@localhost`` and password ``admin``)

Tests
-----

We are using `pytest <https://docs.pytest.org/en/stable/>`_ along with `django-webtest <https://github.com/django-webtest/django-webtest>`_.
Please write tests for new features or fixed bugs. You can use your IDE integration to run the tests or execute the
whole test suite with ``pytest``.

Code style
----------

We are enforcing a good code style for every pull request. To ensure that you only commit appropriate code, we recommend
installing a pre-commit hook with ``pre-commit install``. You can have a look at ``.pre-commit-config.yaml`` to check
how this works. In short it executes the following steps before every commit:

* run ``autoflake`` with a couple of flags to remove unused imports,
* run ``isort .`` to sort imports,
* run ``black .`` to format the code.

If you want to do that manually, run ``pre-commit run --all-files``.
Next to that, we also run ``pylint ephios`` to check for semantic issues in the code.

