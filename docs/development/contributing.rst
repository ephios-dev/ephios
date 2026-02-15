Contributing
============

Contributions to ephios are welcome. If you want to see what we are currently up to, check the available
`issues <https://github.com/ephios-dev/ephios/issues>`_.

If you have an idea for new feature you should start by deciding whether you want to write a plugin (see :doc:`plugins/index`)
or to contribute the feature to the ephios core code. A plugin is usually suitable if the feature is very specific to
a small set of users (e.g. a specific signup process only used in your local organisation) or the feature is not related
to the core tasks of ephios (e.g. a system for stock management). If all ephios users could profit from your feature,
you should consider contributing it to the core code. Please start by describing your feature in a new issue in the
GitHub repository to coordinate the extent with us.
When working on existing issues, please assign yourself and create a pull request early on.

Development setup
-----------------

To set up a development version on your local machine, you need to execute the following steps:

#. Install external packages required for developing ephios

   * ``git`` (to check out the repository)
   * ``python`` version 3.8 or higher including dev and virtualenv tooling
   * ``gettext`` (to compile translations, might also be named ``msgfmt``)

#. Check out the `repository <https://github.com/ephios-dev/ephios>`_ and cd to it
#. Install uv (if not already installed): `Installation guide <https://docs.astral.sh/uv/getting-started/installation/>`_
#. Install dependencies with ``uv sync --dev`` (this might create a virtual environment for you)
#. Create env file with ``cp .env.example .env``
#. Migrate the database with ``uv run manage.py migrate``
#. Prepare files for the installation with ``uv run manage.py build``
#. Load data for testing with ``uv run manage.py devdata``
#. Start the development server with ``uv run manage.py runserver``
#. Open your web browser, visit ``http://localhost:8000`` and log in with the default credentials (user ``admin@localhost`` and password ``admin``)

If those steps did not work for you, please contact us or open an issue in the GitHub repository.
Feel free to adjust how your shell and uv handle virtual environments to your liking.

.. warning::
    The default development server is not suitable for production use. It is not secure and not performant.
    If you want to run ephios in production, please follow the :doc:`deployment guide </admin/deployment/index>`

Tests
-----

We are using `pytest <https://docs.pytest.org/en/stable/>`_ along with `django-webtest <https://github.com/django-webtest/django-webtest>`_.
Please write tests for new features or fixed bugs. You can use your IDE integration to run the tests or execute the
whole test suite with ``uv run pytest``.

Code style
----------

We are enforcing a good code style for every pull request. To ensure that you only commit appropriate code, we recommend
installing a pre-commit hook with ``prek install``. You can have a look at ``.pre-commit-config.yaml`` to check
how this works. In short it executes the following steps before every commit:

* runs ``ruff`` to check for linting and formatting issues and fix them if possible,
* formats HTML templates with ``djhtml``,
* does some whitespace checks

If you want to do that manually, run ``prek run --all-files``.
Next to that, we also run ``uv run pylint src/ephios`` to check for semantic issues in the code.

Translations
------------

We are using the django translation system for translations in python, html and javascript.
After adding new strings to translate, run this to generate
the `locale/**/.po` files for translation:

.. code-block:: bash

   python manage.py makemessages --all -d django
   python manage.py makemessages --all -d djangojs --ignore data --ignore docs

Calling ``makemessages`` in the ``djangojs`` domain will find gettext calls in javascript files in the
current working directory. Therefore, we need to ignore the ``data`` which contains static files from
3rd-party-packages already translated and the ``docs`` directory. Some 3rd-party-javascript comes without
a translation. To add them, do run ``makemessages`` from the ``data/public/static/`` directory after running
``collectstatic``, but ignore all directories of 3rd-party-packages that are already translated, e.g.:

.. code-block:: bash

   cd data/public/static/
   python ../../../manage.py makemessages --all -d djangojs --ignore jsi18n --ignore admin --ignore CACHE --ignore recurrence --ignore select2

We tend to edit our .po files using weblate, but a local editor like poedit works as well.

Using other databases
---------------------

By default, ephios uses a sqlite database for development and PostgreSQL for production.

Postgres
''''''''

If you want to use Postgres in development, here are some steps to follow:

.. code-block:: console

   sudo docker run --name postgres -e POSTGRES_PASSWORD=password -e POSTGRES_DB=ephios -e PGDATA=/tmp -d -p 5432:5432 -v ${PWD}:/var/lib/postgresql/data postgres:latest

Then, you can use the following settings in your .env file. Remember to migrate etc.

.. code-block:: bash

   DATABASE_URL=psql://postgres:password@localhost:5432/ephios

MySQL
''''''

We do not recommend using MySQL, but if you need a mysql for development, you can use the following docker command:

.. code-block:: bash

   sudo docker run --name mysql -e MYSQL_ROOT_PASSWORD=somesupersecret123 -p 3306:3306 -d docker.io/library/mariadb:latest
   sudo docker exec -it mysql mariadb -u root -p  # use the password above
   CREATE DATABASE ephios;


Then, you can use the following settings in your .env file. Remember to migrate etc.

.. code-block:: bash

   DATABASE_URL=mysql://root:somesupersecret123@127.0.0.1:3306/ephios
