# karsk build-wrapper

!!! warning
    This command exists for the developers of Karsk. The wrapper is built
    automatically when needed and is cached between karsk invocations.

## NAME
karsk\-build\-wrapper - (Re-)build the wrapper program

## SYNOPSIS
**karsk build-wrapper** [*options*]

## DESCRIPTION
**karsk build-wrapper** compiles the wrapper program and places it into cache.

Useful to recompile the wrapper if it changes, or during development of the
wrapper program.

## OPTIONS

--8<-- "docs/commands/common-options.md:arch"

--8<-- "docs/commands/common-options.md:engine"

--8<-- "docs/commands/common-options.md:staging"

## SEE ALSO
