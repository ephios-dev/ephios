Base classes
============

Signup Flow
-----------

When writing a custom signup flow, subclass from ``AbstractSignupFlow`` and register your class
with the corresponding signal. There's also ``BaseSignupFlow`` that provides some basic implementations
for common patterns and is used by many of the builtin flows.

.. autoclass:: ephios.core.signup.flow.abstract.AbstractSignupFlow
   :members:
   :undoc-members:
   :private-members:

Shift structure
---------------

When writing a custom signup flow, subclass from ``AbstractShiftStructure`` and register your class
with the corresponding signal. There's also ``BaseShiftStructure`` that provides some basic implementations
for common patterns and is used by many of the builtin flows.

.. autoclass:: ephios.core.signup.structure.abstract.AbstractShiftStructure
   :members:
   :undoc-members:
   :private-members:

Consequences
------------

Implement custom conseqence types by subclassing from ``BaseConsequenceHandler`` and registering
it with the corresponding signal.

.. autoclass:: ephios.core.consequences.BaseConsequenceHandler
   :members:
   :undoc-members:
   :private-members:

Notifications
-------------

Implement custom notification types or backends by subclassing from the following classes and
registering them with the corresponding signal.

.. autoclass:: ephios.core.services.notifications.types.AbstractNotificationHandler
   :members:
   :undoc-members:
   :private-members:
.. autoclass:: ephios.core.services.notifications.backends.AbstractNotificationBackend
   :members:
   :undoc-members:
   :private-members:

.. toctree::
    :maxdepth: 0
