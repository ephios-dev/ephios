Calendar export
===============

To integrate a personalized feed of events into your calendar applications,
use the URL copied from the "Calendar" section in your personal settings.
In most calendar apps (Google Calendar, Apple Calendar, Nextcloud Calendar, Thunderbird, ...)
choose the option to subscribe to a calendar by URL.
You do not need authorization with this URL. It will always be read-only.

The feed will always contain shifts you are confirmed for, with (your individual) start and
end times. With the parameters ``requested=1`` and ``rejected=1`` it will also contain shifts
you have requested participating in or have been rejected from them, respectively. The ICS
``status`` flag will be set accordingly, so your clients can show these events as
"tentative" or "cancelled".
You can remove those parameters to customize the behavior for your needs.

The URL contains a secret to protect unauthorized access to your individual feed.
It can be reset using the button in the settings. Afterwards, all subscriptions need to
be reconfigured using the new secret.

.. toctree::
