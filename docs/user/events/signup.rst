Signup settings
===============

When creating a shift, you need to configure the signup flow and the shift structure.

The signup flow controls **how** users can sign up for the shift and what happens when signing up.

The shift structure configures **who** can sign up for the shift and how personnel is structured.

To cover different use cases, ephios offers different signup flows and shift structures.
Plugins might provide additional flows and structures that can be freely mixed with the default ones.

Available signup flows
-----------------------

Signup flows check how people can sign up for your shift.
Most let you configure whether users who have already been confirmed can
cancel on their own and whether individually deviating start and end times can be
specified when registering.

Direct signup
^^^^^^^^^^^^^

Shifts with this signup methods offer the user a button with the inscription "Participate".
Any user who signs up is immediately confirmed and listed as a participant in the shift.

Request and confirm
^^^^^^^^^^^^^^^^^^^

Shifts with this signup method offer the user a button labeled "Request".
Any user requesting to attend will have their request listed in the disposition.
The people responsible for the event will receive notification of the request.
In the disposition they can then confirm or reject the participation.


Manual disposition
^^^^^^^^^^^^^^^^^^

The ability to sign up for this shift is disabled for all users,
optionally a reason can be specified. Users can be added via the disposition.
This signup flow can be used e.g. for training courses, where the responsible persons
send individual helpers and a self-registration is not intended.

Linked to other shift
^^^^^^^^^^^^^^^^^^^^^

With this signup flow, it is not possible for volunteers to register;
instead, the participants are mirrored from another shift.
The shift to mirror is selected in the settings.
This registration procedure can be used, for example, for courses lasting
several days, where registration is controlled via the first shift and the
participants are automatically registered for all other days/shifts.

Shift structures
----------------

Shift structures control who can sign up for the shift, e.g. minimum age.
They mainly differ by how qualification requirements and personnel counts can be required.

Uniform
^^^^^^^

This is the simplest structure. You can configure min and max participant count
and an optional set of qualifications required.

This is great for trainings and other events where you don't care about a specific distribution
of qualifications or teams.

Qualification mix
^^^^^^^^^^^^^^^^^

Configure min/max counts of participants having some single minimum qualification.

This is great when you require different amounts of people with differing qualification.

Named teams
^^^^^^^^^^^

Configure named teams with individual min/max counts and qualification requirement to
sort participants into. Participants can even be asked for their preferred team.

Disposition
-----------

On the detail page of an event, responsibles of the event can reach the disposition for each shift via the button "Disposition".
There, all participations for the shift are displayed in the corresponding states.

- Requested: The user has requested participation for this shift. The relevant qualifications of the user and additional information such as the preferred section are also displayed. If there is an exclamation mark on the cogwheel, a deviating participation time or comment was entered during registration. These can be viewed by clicking on the cogwheel.
- Rejected by responsible person: the participation was rejected by a responsible person via the disposition.
- Declined by participant: the helping person has declined for this shift.
- Confirmed: participation was confirmed by a responsible person. Here (if needed) further details like the assigned section can be entered. The participant can be assigned for a different time via the cogwheel.
- Add more: Using the search field, participation can be created for additional users who have not previously signed up for this shift. If no user is found for the entered name, ephios offers the possibility to create a placeholder with this name. This can be used, for example, if external helpers without an account are to be assigned.

The state of a participation can be changed by moving the entry into
the desired field. For example, a requested participation can be confirmed by
moving it to the "Confirmed" field. The changes must then be confirmed with "Save".

.. toctree::
    :maxdepth: 2
