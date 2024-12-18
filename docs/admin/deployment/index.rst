Deploying ephios
================

This section shows how to deploy ephios in a production environment.

Prerequisites
-------------

To run ephios (a django project) in production, you generally need:

- A **python** environment (we recommend python3.11).
- A **WSGI application server** (we recommend gunicorn). This will be the program that actually runs the ephios code.
  Do not use `manage.py runserver` in production.
- A **reverse proxy** (we recommend nginx) that handles TLS termination, serves static files and
  proxies requests to the WSGI application server. You should also secure your server using a firewall.
- A **database** (we recommend postgresql) that stores the ephios data.
- A program (e.g. **cron**) that periodically runs a management command (e.g. to send notifications).
- A **redis** instance that is used for caching.
- An **SMTP server** for sending emails.
- A domain pointing to your server and a TLS certificate for it.


Installation
------------

Generally, ephios can be installed like most django projects.
We prepared some guides for common deployment scenarios:

.. toctree::
    :maxdepth: 1

    manual/index
    docker/index


Securing your installation
--------------------------

ephios is a web application and as such it is exposed to the internet. It is therefore important to
take some security measures to protect your user data.

You are already using SSL, which is a good start. You should also make sure that your server is
up-to-date and that you have a firewall configured to only allow access to the ports you need.

SSL
~~~

You might want to check out `this Mozilla page <https://mozilla.github.io/server-side-tls/ssl-config-generator/>`_ on
how to configure your SSL ciphers and protocols.

HSTS
~~~~

The `HSTS header <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security>`_
is set by ephios to a default of 1 day. After you confirmed your pages and assets are served via
SSL correctly, you should increase this value to a year.
To do so, add the following environment variables to your ephios environment:

.. code-block::

    SECURE_HSTS_SECONDS=31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS=True
    SECURE_HSTS_PRELOAD=True

Restart and maybe also add your domain to the `HSTS preload list <https://hstspreload.org/>`_.

Troubleshooting
---------------

You can find the logs of the ephios application inside
the ``DATA_DIR``, e.g.
``/var/ephios/data/private/logs``.

Error with None values for date fields when using MySQL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are using MySQL, you might encounter errors on date computations like this:

.. code-block::

    TypeError: "Exception Value: '<' not supported between instances of 'NoneType' and 'NoneType'"

This may be caused by MySQL `missing timezone information <https://stackoverflow.com/a/60844090/4837975>`_.
You can fix this by running:

.. code-block:: console

    # mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -u root -p mysql

"Data too long for column" Error when using MariaDB 10.7+
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are upgrading your existing ephios setup to MariaDB 10.7+, you might encounter problems
with "Data too long for column" errors. These might be caused by a change in how django handles
UUID fields with MariaDB. Try this management command to migrate your existing database:

.. code-block:: console

    # sudo -u ephios -i
    $ export ENV_PATH="/home/ephios/ephios.env"
    $ source /home/ephios/venv/bin/activate
    $ python -m ephios convert_mariadb_uuids
