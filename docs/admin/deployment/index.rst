Deploying ephios
================

This section shows how to deploy ephios in a production environment.

.. note:: This page is work in progress. Feel free to contribute. Either way, ephios can be deployed like most django apps.


.. toctree::
    :maxdepth: 2


Logging
-------

In production, ephios logs to a file at `LOGGING_FILE` configured in the environment.
The file is rotated daily, copies are kept for `LOGGING_BACKUP_DAYS` days (default 14).

Also, ephios sends emails to the `ADMINS` configured in the environment on errors.

Feel free to further specify the `LOGGING` dict in your own django settings file.