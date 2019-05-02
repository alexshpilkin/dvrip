Changes
=======

Unreleased
----------

* Files can now be listed with ``dvr find`` and downloaded (to standard
  output) with ``dvr cat``.
* Device can now be rebooted with ``dvr reboot``.
* System time can now be set using ``dvr time``, using ``dateparser``.
* The ``dvr info`` tool reports system time alongside uptime.
* Connection classes are now in ``dvrip.io``.
* The ``test_connect`` development script is renamed to ``dvrip_test``.
* The ``dvr`` tool can now be launched under Windows.
* Broken dependency on Python 3.7 and broken development dependencies on
  ``mock`` and ``typing_extensions`` are fixed.

0.0.1 (2019-04-30)
------------------

* Initial release.
