# Common options

Several Karsk commands share the same options. They are documented once on
this page, and each command's OPTIONS section includes the entries that apply
to it.

<!-- --8<-- [start:staging] -->
#### **--staging** *path*

Path to the staging area. Defaults to `./staging`.
<!-- --8<-- [end:staging] -->

<!-- --8<-- [start:engine] -->
#### **--engine** *engine-name*

Which OCI engine to use, either *podman* or *docker*. See
[OCI engines](../concepts.md#oci-engines) for more information.
<!-- --8<-- [end:engine] -->

<!-- --8<-- [start:arch] -->
#### **--arch** *arch*

CPU architecture to use. One of *native* (the host's architecture, the
default), *target* (amd64), *amd64* or *arm64*.
<!-- --8<-- [end:arch] -->
