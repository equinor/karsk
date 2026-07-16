# karsk test

## NAME
karsk\-test - Test Karsk packages using pytest

## SYNOPSIS
**karsk test** [*options*] *config* [*pytest-args*...]

## DESCRIPTION
**karsk test** uses [pytest](https://pytest.org) to run the tests in the directory referenced by the *config* file's `tests` field. The command errors if the config has no `tests` field.

In addition to the standard repertoire provided by pytest, this command provides the **karsk** fixture: the pre-configured [`karsk.context.Context`](../api/context.md) for your configuration, which lets tests locate built packages and run programs inside the build environment. See the [testing guide](../testing.md).

## OPTIONS

--8<-- "docs/commands/common-options.md:engine"

--8<-- "docs/commands/common-options.md:staging"

## SEE ALSO
