Signup methods
==============

To cover different use cases, ephios offers different signup methods. In the following, the provided logon procedures are explained, but additional signup methods can also be integrated as a plugin.

When creating a shift, a signup method has to be selected. This controls how users can sign up for the shift and what happens after signing up. 

Availabe signup methods
-----------------------
Instant confirmation
^^^^^^^^^^^^^^^^^^^^

Shifts with this signup methods offer the user a button with the inscription "Participate". Any user who signs up is immediately confirmed and listed as a participant in the shift.

The shift settings can specify conditions that a user must meet in order to participate. These include a minimum age and a registration deadline. In addition, a minimum and a maximum number of participants can be specified. If the maximum number of participants is reached, no further users can register. Furthermore, required qualifications can be specified. Users must have all the specified qualifications to be able to participate.

In addition, it can be set whether users who have already been confirmed can cancel on their own and whether individually deviating start and end times can be specified when registering.

Request and confirm
^^^^^^^^^^^^^^^^^^^

Shifts with this registration procedure offer the user a button labeled "Request". Any user requesting to attend will have their request listed in the disposition. The persons responsible for the event will receive notification of the request. In the disposition they can then confirm or reject the participation. 

The same settings can be made for this signup method as for "Instant confirmation".

Section based signup
^^^^^^^^^^^^^^^^^^^^

This signup method works in the same way as "Request and confirm". In addition, several sections can be defined in the shift settings. For each section, a minimum and maximum number of participants can be specified. Also per section the required qualifications can be specified. Users must have all of the specified qualifications to participate in that section. Sections with mixed qualifications (e.g., RTW with 1x RS, 1x NFS) must either be mapped as multiple sections or use a different signup method.

Users can specify a preferred section when requesting participation. It can be set in the shift settings that this specification is mandatory. The preferred section is visible in the disposition.

No registration (disposition only)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ability to sign up for this shift is disabled for all users, optionally a reason can be specified. Users can be added via the disposition. This registration procedure can be used e.g. for training courses, where the responsible persons send individual helpers and a self-registration is not intended.

Linked to other shift
^^^^^^^^^^^^^^^^^^^^^

With this registration method, it is not possible for volunteers to register; instead, the participants are mirrored from another shift. The shift to mirror is selected in the settings. This registration procedure can be used, for example, for courses lasting several days, where registration is controlled via the first shift and the participants are automatically registered for all other days/shifts.

Disposition
^^^^^^^^^^^

On the detail page of an event, responsibles of the event can reach the disposition for each shift via the button "Disposition". There, all participations for the shift are displayed in the corresponding states.

- Requested: The user has requested participation for this shift. The relevant qualifications of the user and additional information such as the preferred section are also displayed. If there is an exclamation mark on the cogwheel, a deviating participation time or comment was entered during registration. These can be viewed by clicking on the cogwheel.
- Rejected by responsible person: the participation was rejected by a responsible person via the disposition.
- Declined by participant: the helping person has declined for this shift.
- Confirmed: participation was confirmed by a responsible person. Here (if needed) further details like the assigned section can be entered. The participant can be assigned for a different time via the cogwheel.
- Add more: Using the search field, participation can be created for additional users who have not previously signed up for this shift. If no user is found for the entered name, ephios offers the possibility to create a placeholder with this name. This can be used, for example, if external helpers without an account are to be assigned.

The state of a participation can be changed by moving the entry into the desired field. For example, a requested participation can be confirmed by moving it to the "Confirmed" field. The changes must then be confirmed with "Save".

.. toctree::
    :maxdepth: 0