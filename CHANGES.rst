Changes
=======

Unreleased
----------

* Sizes are now displayed in GNU 'human-readable' format (2K, 31M, etc.)
  using ``humanize`` when ``dvr find`` is given the ``-h`` flag.

0.0.2 (2019-05-02)
------------------

* Files can now be listed with ``dvr find`` (depends on ``dateparser``)
  and downloaded (to standard output) with ``dvr cat``.
* Device can now be rebooted with ``dvr reboot``.
* System time can now be set using ``dvr time`` (depends on
  ``dateparser``).
* The ``dvr info`` tool reports system time alongside uptime.
* Connection classes are now in ``dvrip.io``.
* The ``test_connect`` development script is renamed to ``dvrip_test``.
* The ``dvr`` tool can now be launched under Windows.
* Broken dependency on Python 3.7 and broken development dependencies on
  ``mock`` and ``typing_extensions`` are fixed.

0.0.1 (2019-04-30)
------------------

* Initial release.
