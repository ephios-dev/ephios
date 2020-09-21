![ephios](https://github.com/ephios-dev/ephios/workflows/ephios/badge.svg)
# ephios
ephios is a tool to manage shifts for medical services.

## Development setup

To set up a development version on your local machine, you need to execute the following steps:
1. Check out repository and cd to it
2. Set up a virtualenv for the project with Python >=3.8 and activate it
3. Install poetry (if not already installed): `curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python`
4. Install dependencies with `poetry install`
5. Create env file with `cp .env.example .env`
6. Migrate the database with `python manage.py migrate`
7. Compile translations with `python manage.py compilemessages`
8. Load data for testing with `python manage.py setupdata debug`
9. Start the development server with `python manage.py runserver`
10. Open your web browser, visit `http://localhost:8000` and log in with the default credentials (user `admin@localhost` and password `admin`)

Before committing, make sure to lint your changes with `black .`. You can also check the [IDE integration](https://github.com/psf/black#editor-integration) or install a pre-commit hook with `pre-commit install` (recommended). You also need to to test the code with `pytest`.
