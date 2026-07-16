# karsk install

## NAME
karsk\-install - Install a Karsk environment

## SYNOPSIS
**karsk install** [*options*] *config*

## DESCRIPTION
**karsk install** copies the packages built by [karsk build](build.md) from the
staging area to the *destination* directory defined in the *config* file, and
assembles a deployment there.

In particular, this command ensures that:

- Only new store items are copied
- The build ID in the environment name (`<version>+<build_id>`) is allocated
  against what already exists at the destination.
- If an environment with an identical manifest already exists, no new
  environment is created.
- Existing builds are never overwritten or removed; only the `latest`/`stable`
  symlinks (and any configured links) are
  updated.

## OPTIONS

--8<-- "docs/commands/common-options.md:engine"

--8<-- "docs/commands/common-options.md:staging"
  
## NOTES

Unlike to [**karsk sync**](./karsk-sync), this command copies data from staging to the destination on localhost, creating a fresh build ID if needed, among other things.

## SEE ALSO
