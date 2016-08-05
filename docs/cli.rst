======================
Command line interface
======================

The nova tool
=============

The ``nova`` tool is used to manage a working directory and is run from the
command line. The entire functionality is available as a set of subcommands to
the program.

.. program:: nova

All subcommands can receive the following two options:

.. option:: --remote <remote>

    URL of the remote NOVA server.

.. option:: --token <token>

    Authentication token for registration.

Except for the ``init`` command, these parameters are read from a
dataset-specific or global configuration file.


init
----

.. program:: nova init

Registers the current directory with the server.

.. option:: --name <name>

    Name of the dataset.

If :option:`--name` is not given, the current directory name is used.


list
----

.. program:: nova list

Lists all available datasets that can be cloned or pushed to.


push
----

.. program:: nova push

Pushes the data in the current working directory to the remote server.


clone
-----

.. program:: nova clone

Retrieves an existing dataset from the remote server.

.. option:: --id <id>

    Numerical identifier of the dataset.

.. option:: --name <name>

    Alternative directory name for the cloned working directory.


close
-----

.. program:: nova close

Closes a dataset to prevent further modification.

.. note::

    Of course you can continue modifying *local* data, however any attempts to
    push such a working directory will be denied.


Configuration
=============

All settings of a given dataset are stored in a local configuration file called
``.nova/config`` like this:

.. code-block:: ini

        [core]
        remote = https://nova.server.somewhere
        token = 1.PnaQ8MN7Gmt5WDgn5jrBfjtV_Wo
        id = 1

It contains access information to avoid having to pass this through command line
arguments. You can copy this file to ``~/.config/nova/config`` in case you want
to avoid typing the access credentials when initializing a dataset.
