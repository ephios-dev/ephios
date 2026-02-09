Manual installation
~~~~~~~~~~~~~~~~~~~

To run ephios on a debian-based system, make sure you have prepared the prerequisites.
What follows is a rough guide to install ephios and configure the supporting services.
Feel free to adapt it to your needs and style. The guide assumes you are logged in as root
(``#`` is a root prompt, ``$`` the ephios user prompt).

Unix user
'''''''''

Create a unix user that will run the ephios. You should avoid running ephios with root privileges.

.. code-block:: console

    # adduser --disabled-password --home /home/ephios ephios

Package dependencies
''''''''''''''''''''

Install the system packages that ephios depends on.

.. code-block:: console

    # apt-get install gettext

python environment and ephios package
'''''''''''''''''''''''''''''''''''''

Create a `virtualenv <https://docs.python.org/3/tutorial/venv.html>`_ for ephios and
install the ephios package. You may need to specify an exact python executable (e.g. ``python3.13``)
Replace pgsql with mysql if you want to use mysql.

.. code-block:: console

    # sudo -u ephios python3 -m venv /home/ephios/venv
    # sudo -u ephios /home/ephios/venv/bin/pip install gunicorn "ephios[redis,pgsql]"

Database
''''''''

Create a database user and a database for ephios. For postgres this could look like this:

.. code-block:: console

    # sudo -u postgres createuser ephios
    # sudo -u postgres createdb -O ephios ephios

Make sure the encoding of the database is UTF-8.

Data directory
''''''''''''''

ephios stores some data in the file system. Create the folders and make sure the ephios user can write to them.
The reverse proxy needs to be able to read the static files stored in ``/var/ephios/data/public/static``.

.. code-block:: console

    # mkdir -p /var/ephios/data/
    # chown -R ephios:ephios /var/ephios

Config file
'''''''''''

ephios can be configured using environment variables. They can also be read from a file.
Create a file ``/home/ephios/ephios.env`` (owned by the ephios user) with the following
content, replacing the values with your own:

.. code-block::

    DEBUG=False
    DATA_DIR=/var/ephios/data
    DATABASE_URL=psql://dbuser:dbpass@localhost:5432/ephios
    ALLOWED_HOSTS="your.domain.org"
    SITE_URL=https://your.domain.org
    EMAIL_URL=smtp+ssl://emailuser:emailpass@smtp.domain.org:465
    DEFAULT_FROM_EMAIL=ephios@domain.org
    SERVER_EMAIL=ephios@domain.org
    ADMINS=Org Admin <admin@domain.org>
    CACHE_URL="redis://127.0.0.1:6379/1"


For details on the configuration options and syntax, see :ref:`configuration options <env_file_options>`.

To test your configuration, run:

.. code-block:: console

    # sudo -u ephios -i
    $ export ENV_PATH="/home/ephios/ephios.env"
    $ source /home/ephios/venv/bin/activate
    $ python -m ephios check --deploy
    $ python -m ephios sendtestemail --admin

Build ephios files
''''''''''''''''''

Now that the configuration is in place, we can build the static files and the translation files.

.. code-block:: console

    # sudo -u ephios -i
    $ export ENV_PATH="/home/ephios/ephios.env"
    $ source /home/ephios/venv/bin/activate
    $ python -m ephios migrate
    $ python -m ephios build

Setup cron
''''''''''

ephios needs to have the ``run_periodic`` management command run periodically (at least every five minutes).
This command sends notifications and performs other tasks that need to be done regularly.
Run ``crontab -e -u ephios`` and add the following line:

.. code-block:: bash

    */5 * * * * ENV_PATH=/home/ephios/ephios.env /home/ephios/venv/bin/python -m ephios run_periodic

Setup gunicorn systemd service
''''''''''''''''''''''''''''''

To run ephios with gunicorn, create a systemd service file ``/etc/systemd/system/ephios-gunicorn.service``
with the following content:

.. code-block:: ini

    [Unit]
    Description=ephios gunicorn daemon
    After=network.target

    [Service]
    Type=notify
    User=ephios
    Group=ephios
    WorkingDirectory=/home/ephios
    Environment="ENV_PATH=/home/ephios/ephios.env"
    ExecStart=/home/ephios/venv/bin/gunicorn ephios.wsgi --name ephios \
                --workers 5 --max-requests 1000  --max-requests-jitter 100 --bind=127.0.0.1:8327
    Restart=on-failure

    [Install]
    WantedBy=multi-user.target

To start the service run:

.. code-block:: console

    # systemctl daemon-reload
    # systemctl enable ephios-gunicorn
    # systemctl start ephios-gunicorn


Configure reverse proxy
'''''''''''''''''''''''

Configure your reverse proxy to forward requests to ephios. For nginx, you can start with this:

.. code-block:: nginx

    server {
        listen 80 default_server;
        listen [::]:80 ipv6only=on default_server;
        server_name your.domain.org
        location / {
            return 301 https://$host$request_uri;
        }
    }

    server {
        listen 443 ssl;
        listen [::]:443 ipv6only=on ssl;
        server_name your.domain.org;

        http2 on;
        ssl_certificate     /etc/letsencrypt/certificates/your.domain.org.crt;
        ssl_certificate_key /etc/letsencrypt/certificates/your.domain.org.key;

        location / {
            proxy_pass http://localhost:8327;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
            proxy_set_header Host $http_host;
            proxy_redirect off;
        }

        location /static/ {
            alias /var/ephios/data/public/static/;
            access_log off;
            expires 1d;
            add_header Cache-Control "public";
        }

        location /usercontent/ {
            internal;
            alias /var/ephios/data/private/media/;
        }
    }

For apache you can build on this:

.. code-block:: apache

    <VirtualHost *:80>
        ServerName your.domain.org
        Redirect permanent / https://your.domain.org/
    </VirtualHost>

    <VirtualHost *:443>
        ServerName your.domain.org
        SSLEngine on
        SSLCertificateFile /etc/letsencrypt/certificates/your.domain.org.crt
        SSLCertificateKeyFile /etc/letsencrypt/certificates/your.domain.org.key

        ProxyPass /static/ !
        Alias /static/ /var/ephios/data/public/static/
        <Directory /var/ephios/data/public/static/>
            Require all granted
        </Directory>

        RequestHeader set X-Forwarded-Proto "https"
        ProxyPreserveHost On
        ProxyPass / http://localhost:8327/
        ProxyPassReverse / http://localhost:8327/
    </VirtualHost>

Please note that `FALLBACK_MEDIA_SERVING` needs to be set to `True` in the ephios configuration when using apache.

Remember to replace all the domain names and certificate paths with your own.
Make sure to use secure SSL settings.
To obtain SSL certificates, you can use `certbot <https://certbot.eff.org/>`_ with Let's Encrypt.

Next steps
''''''''''

After restarting your reverse proxy you should be able to access ephios at https://your.domain.org.
You can now create your first user account by running:

.. code-block:: console

    # sudo -u ephios -i
    $ export ENV_PATH="/home/ephios/ephios.env"
    $ source /home/ephios/venv/bin/activate
    $ python -m ephios createsuperuser

You should now secure your installation. Try starting with the tips in the security section.

To install a plugin install them via pip:

.. code-block:: console

    # sudo -u ephios -i
    $ export ENV_PATH="/home/ephios/ephios.env"
    $ source /home/ephios/venv/bin/activate
    $ pip install "ephios-<plugin>"
    $ python -m ephios migrate
    $ python -m ephios build

To update ephios create a backup of your database and files and run:

.. code-block:: console

    # sudo -u ephios -i
    $ export ENV_PATH="/home/ephios/ephios.env"
    $ source /home/ephios/venv/bin/activate
    $ pip install -U "ephios[redis,pgsql]"
    $ python -m ephios migrate
    $ python -m ephios build

After installing plugins or updating, restart the gunicorn service:

.. code-block:: console

    # systemctl restart ephios-gunicorn
