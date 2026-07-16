# karsk-build

## NAME
karsk\-build - Build a Karsk configuration locally

## SYNOPSIS
**karsk build** [*options*] *config*

## DESCRIPTION
**karsk build** fetches and builds every package in the *config* file and places the result in the staging area.

Karsk uses an [OCI engine](../concepts.md#oci-engines) like
[Podman](https://podman.io) or [Docker](https://docker.io) to build each package
specified in the configuration in a sandbox, ensuring that the final binaries
are built in a way that is compatible with a target system.

The *config* file contains a *build-image* field, which is a relative path to a
OCI-compatible Containerfile. This describes the build environment that all
packages will use. Any system-level build dependencies and runtime assumptions
should be present in this file.

Packages are built in dependency order, and packages that already exist in the
staging area or at the destination are skipped. After the packages are built,
the staging area contains the same layout as a deployment:

- `store` directory with the built packages
- `versions` directory with the assembled environment
- `bin` directory with the configured entrypoints.

## OPTIONS

#### **--package** *name*

Build up to and including the package *name*, then stop.

--8<-- "docs/commands/common-options.md:arch"

--8<-- "docs/commands/common-options.md:engine"

--8<-- "docs/commands/common-options.md:staging"

## SEE ALSO
[karsk-enter](enter.md), [karsk-test](test.md), [karsk-install](install.md),
[Concepts](../concepts.md)
