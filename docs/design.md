# NOVA data management

## Goals

The main goal of the system is to provide *users* and *groups* of users remote
access to *datasets*. The workflow should center around users accessing files
locally but allow mirroring datasets remotely. To facilitate larger compute
resources, non-attending remote computation should be made possible too.

### Related and prior work

* dCache
* iCAT

## Overview

### Datasets

In a generic sense datasets are files and directories of files and can either be
*original* root datasets or *derived* from a parent dataset. For example, a
tomographic scan yielding dark, reference and projection frames is the origin
for subsequent datasets that might contain sinograms, reconstructions,
segmentations and final analysis.

Datasets are *owned* by one user but can be given *read* access to other users
and groups of users.

#### Typed datasets

A generic dataset covers all kinds of data but cannot be used to deduce
information for automatic processing. Hence, a hierarchy of types with
pre-determined attributes is required.

### Architecture

The system is based on a client-server architecture. The server manages user
roles, authorization, authentication and remote data storage. Moreover, it
provides a managing system view for web clients as well as an API view for
programmatic access. This API is consumed by a local client to

1. create a new dataset from a local directory,
2. list available datasets for *cloning* and *deletion* as well as
3. push data to the remote server.

#### Token-based authentication

Storing user name and password for the local client is not advised, hence each
user can generate a token that is used by the API to authenticate and authorize
resource access.

## Technical details
