Contributing
============

Contributions to ephios are welcome. Please check the available `issues <https://github.com/ephios-dev/ephios/issues>`_ first.

Development setup
-----------------

To set up a development version on your local machine, you need to execute the following steps:

#. Check out repository and cd to it
#. Set up a virtualenv for the project with Python >=3.8 and activate it
#. Install poetry (if not already installed): ``curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python``
#. Install dependencies with ``poetry install``
#. Create env file with ``cp .env.example .env``
#. Migrate the database with ``python manage.py migrate``
#. Compile translations with ``python manage.py compilemessages`` and ``python manage.py compilejsi18n``
#. Load data for testing with ``python manage.py setupdata debug``
#. Start the development server with ``python manage.py runserver``
#. Open your web browser, visit ``http://localhost:8000`` and log in with the default credentials (user ``admin@localhost`` and password ``admin``)

Tests
-----

Test the code with ``pytest``.

Code style
----------

We recommend installing a pre-commit hook with ``pre-commit install``. That will (look at ``.pre-commit-config.yaml``) before every commit

* run ``autoflake`` with a couple of flags to remove unused imports,
* run ``isort .`` to sort imports,
* run ``black .`` to format the code. You can also check out the `IDE integration <https://github.com/psf/black#editor-integration>`_

If you want to do that manually, run ``pre-commit run --all-files``. Next to that, we also run ``pylint ephios`` to check for semantic issues in the code.

