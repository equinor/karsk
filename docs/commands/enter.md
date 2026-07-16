# karsk enter

## NAME
karsk\-enter - Enter a Karsk environment

## SYNOPSIS
**karsk enter** [*options*] *config* [*args*...]

## DESCRIPTION
**karsk enter** starts a container session that lets you try out software built
with [karsk build](build.md).

If *args* are not specified, an interactive bash session is started. If *args*
are specified, the given command is executed instead.

The session contains the store and everything described by the *config* at their
destination location, with the destination's *path* being prepended to the
session's `$PATH` variable, effectively giving you the same environment as on
your target machine.

Additionally, your system's `$HOME` is mounted so you can run the software on
your data.

## OPTIONS

#### **--volume**, **-v** *SRC:DST[:ro|rw]*

Mount a volume (in addition to the destination paths and `$HOME`) into the
session. *SRC* must be an existing path on the host, *DST* is the path inside
the container, and the optional mode is `ro` or `rw` (default `rw`). This option
may be repeated to mount more volumes.

--8<-- "docs/commands/common-options.md:arch"

--8<-- "docs/commands/common-options.md:engine"

--8<-- "docs/commands/common-options.md:staging"

## SEE ALSO
