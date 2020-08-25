![jep](https://github.com/jeriox/jep/workflows/jep/badge.svg)
# jep
JEP is a tool to manage shifts for medical services.

## Development setup

To set up a development version of jep on your local machine, you need to execute the following steps:
1. Set up Python >3.8 and a virtualenv for the project
2. Install poetry (if not already installed): `curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python`
3. Check out repository and cd to it
4. Install dependencies with `poetry install`
5. Create env file with `cp .env.example .env`
6. Migrate the database with `python manage.py migrate`
8. Start the development server with `python manage.py runserver`
9. Open yout web browser, visit `http://localhost:8000` and log in with the default credentials (user `admin@localhost` and password `admin`)

Before commiting, make sure to lint your changes with `black .`. You can also check the [IDE integration](https://github.com/psf/black#editor-integration) or install a pre-commit hook with `pre-commit install` (recommended). You also need to to test the code with `python manage.py test`.