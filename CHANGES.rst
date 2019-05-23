Changes
=======

Unreleased
----------

* The ``dvr`` tool can now invoke standalone scripts: ``dvr foo``
  searches for ``dvr-foo`` in the system PATH.
* The ``dvr neigh`` command is now ``dvr discover``.
* ControlMessage and ControlRequest are now simply Message and Request,
  as there is no other kind of message or request.
* The ``search`` module is now ``files``, and so is the corresponding
  DVRIPClient method.
* The ``dateparser`` and ``humanize`` dependencies are now only required
  when the corresponding command-line options are used.

0.0.3 (2019-05-03)
------------------

* DVRs on the current network can now be listed with ``dvr neigh``.
  This command does not require a hostname.
* For all other commands, which do require a hostname, it should now be
  passed using the ``-h`` option to ``dvr``.
* Live video from camera N can now be obtained by passing ``monitor:N``
  to ``dvr cat``.  Append ``;hd`` or ``;sd`` to select the corresponding
  stream, and mind the shell quoting.
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
