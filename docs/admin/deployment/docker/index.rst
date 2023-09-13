Docker
======

Docker Image
------------

We automatically build a Docker image for every release.
It uses gunicorn as a WSGI-server and still requires a
database, redis and some ssl-terminating webserver/proxy
to be set up.

The image is available on the Github Container Registry.

Deployment with Docker Compose
------------------------------

We provide a basic docker-compose file that adds
nginx, postgres and redis to the mix and exposes
the app on port 80. You still need to either provide
an SSL-terminating proxy in front of it or
configure the nginx container to do so.

The compose file can be found at
``deployment/compose/docker-compose.yml`` and
`on github <https://github.com/ephios-dev/ephios/blob/main/deployment/compose/docker-compose.yml>`_.
Feel free to use it as a starting point for your own deployment.

The container defines two volumes for the database and
ephios data files. You should mount them to a persistent
location on your host.

Make sure to change the environment variables in the
compose file to your needs. Have a look at
the :ref:`configuration options <env_file_options>`.

To start the compose file and add a first superuser run:

.. code-block:: console

    # cd deployment/compose/
    # docker compose up --build
    # docker exec -it compose-ephios-1 python -m ephios createsuperuser

If you want to test the container without https, that's
only possible by changing it the compose file:

.. code-block:: yaml

   DEBUG: "True"
   TRUST_X_FORWARDED_PROTO: "False"

The first line enables debug mode and therefore disables a redirect from http to https.
The second line disables trusting the X-Forwarded-Proto header set to https by the nginx
container, which is required for djangos CSRF protection to not kick in on http requests.