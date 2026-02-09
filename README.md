[![tests](https://github.com/ephios-dev/ephios/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/ephios-dev/ephios/actions/workflows/tests.yml)
[![Documentation Status](https://readthedocs.org/projects/ephios/badge/?version=latest)](https://docs.ephios.de/en/latest/?badge=latest)
[![PyPI](https://img.shields.io/pypi/v/ephios)](https://pypi.org/project/ephios/)
[![Coverage Status](https://coveralls.io/repos/github/ephios-dev/ephios/badge.svg?branch=main)](https://coveralls.io/github/ephios-dev/ephios?branch=main)
[![translated by Weblate](https://hosted.weblate.org/widgets/ephios/-/svg-badge.svg)](https://hosted.weblate.org/engage/ephios/)

<h1 align="center">
    <img src="https://raw.githubusercontent.com/ephios-dev/ephios/refs/heads/main/docs/_static/img/ephios_logo.png" alt="ephios logo" width="200">
</h1>

ephios is a web-based system to manage personnel taking part in multiple events. It focuses on a clean, mobile first interface for participants and flexible configuration options for planners. ephios was created by volunteers of german aid organizations and is used by medical services, volunteer organisations and professional associations, among others, to plan helpers at their events.

ephios is free and open-source software with a growing community and a german translation.
We do offer [paid hosting and support](https://ephios.de), feel free to reach out.

- [Features](#features)
- [Getting started](#getting-started)
- [Contributing](#contributing)

## Features

* Single Sign On (OIDC), user management, group based permissions
* Events with shifts, event types with default values for event-specific visibility
* powerful qualification system with flexibile per-shift requirement configuration options
* various signup flows, deadlines, disposition with comments
* track working hours with statistics and approval workflow
* bulk-copy events or export/print as pdf
* log of who made changes to users and events
* progressive web app, calendar export, email and push notifications
* guests and federation, document upload, content pages, ...
* REST-API, plugin system, OAuth2 for external apps

<img src="https://raw.githubusercontent.com/ephios-dev/ephios/refs/heads/main/docs/_static/img/screenshot_event_detail.png" alt="event detail page of some test event with description and multiple shifts">

## Getting started

ephios is built on the python django web framework with plain html/css/js and some uncompiled vue frontend components. Most of what you need to know to get started is in [the documentation](https://docs.ephios.de/en/stable/index.html). We also offer [managed hosting](https://ephios.de) - feel free to reach out.

* [deployment instructions (native and docker)](https://docs.ephios.de/en/stable/admin/deployment/index.html)
* [a user guide explaining many of the features](https://docs.ephios.de/en/stable/user/index.html)
* [API documentation](https://docs.ephios.de/en/stable/api/index.html)
* [building plugins](https://docs.ephios.de/en/stable/development/plugins/introduction.html)

## Contributing
Contributions to ephios are very welcome! Feel free to ask us for what can be done, we might have some additional context. We love to see other people work with ephios and try to help along the way.

Report bugs [on github](https://github.com/ephios-dev/ephios/issues/new?template=bug-report.md). Fork the project and create a pull request to contribute code.
You can find information about the **development setup** in [the documentation](https://docs.ephios.de/en/latest/development/contributing.html)
We are using Weblate for translations, you can also contribute [there](https://hosted.weblate.org/engage/ephios/).
Please follow our [code of conduct](https://github.com/ephios-dev/ephios/blob/main/CODE_OF_CONDUCT.md).
