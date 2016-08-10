========
Concepts
========

The main goal of the system is to provide *users* and *groups* of users remote
access to *datasets*. The workflow should center around users accessing files
locally but allow mirroring datasets remotely. To facilitate larger compute
resources, non-attending remote computation should be made possible too.


Datasets
========

In a generic sense datasets are files and directories of files Datasets are
*owned* by one user but can be given *read* access to other users and groups of
users.

Dataset can either be *original* root datasets or *derived* from a parent
dataset. For example, a tomographic scan yielding dark, reference and projection
frames is the origin for subsequent datasets that might contain sinograms,
reconstructions, segmentations and final analysis. To derive a dataset from
another, the original dataset must be *closed* to prevent modifications and
provide a reproducible chain of intermediate results.


Typed datasets
--------------

A generic dataset covers all kinds of data but cannot be used to deduce
information for automatic processing. Hence, a hierarchy of types with
pre-determined attributes is required.

Types will also help to provide dataset-specific previews. For generic datasets
only a vague file browser kind of preview is possible. For known datasets we can
provide specific previewers, for example a WebGL-based 3D visualization for a
reconstruction or segmented volume.

.. _programmatic-derivation:

Programmatic derivation
-----------------------

Besides manual derivation by the user, it should be possible to let a background
program process an input dataset on behalf of a user.


Architecture
============

The system is based on a client-server architecture. The server manages user
roles, authorization, authentication and remote data storage.  The system
distinguishes between the actual dataset whose data and metadata is managed by
the server and a local *working directory* containing a copy of the datasets' data.
The user either declares an existing working directory to be a dataset by
*initializing* and registering it with the server or checking out and retrieving
the data into a working directory. The user *pushes* the working directory
for the sake of synchronizing the remote and the local state.

.. note::

    From my point of view pushing is *not* the place for commit-like actions,
    i.e.  denoting a new version or whatever but merely storing the data
    remotely. But this point is open for discussion.

The server provides a managing system view for web clients as well as an API
view for programmatic access. This API is consumed by a local client to

1. create a new dataset from a local directory,
2. list available datasets for *cloning* and *deletion* as well as
3. push data to the remote server.


Token-based authentication
--------------------------

Storing user name and password for the local client is not advised, hence each
user can generate a token that is used by the API to authenticate and authorize
resource access. To prevent third-party abuse, tokens can be revoked at any
time.

Token-based authentication is also used for :ref:`programmatic-derivation` in
which server-side processes use the authentication token to implement data
processing on behalf of the user.


Error handling
--------------

All server-side errors must be mapped to appropriate HTTP status codes with a
JSON response detailing the error.


Related and prior work
======================

* dCache
* iCAT
