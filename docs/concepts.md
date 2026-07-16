# Concepts

--8<-- "README.md:how-it-works"

## Anatomy of a deployment

Both the staging area and the destination share the same layout:

```
<base>/
├── store/                        ← one directory per built package
│   └── <hash>-<name>-<version>/
├── versions/                     ← one environment per build
│   ├── <version>+<build_id>/
│   ├── latest -> <version>+<build_id>
│   └── stable -> latest
└── bin/                          ← user-facing entrypoints
    ├── .wrapper
    └── <entrypoint> -> .wrapper
```

### The Store (`store/`)

Every package is built into `store/<hash>-<name>-<version>`. The hash covers
the package's configuration, its source, the build image and all of its
dependencies, so two builds with the same hash are interchangeable.

Because builds run in a container with dependencies mounted at their
*destination* store paths, paths embedded at build time (such as rpaths) stay
valid after installation.

### Versions and manifests (`versions/`)

An *environment* under `versions` is a regular directory containing symlinks
into the store, combining the main package with all of its dependencies. Each
environment contains a `manifest` file identifying exactly which store paths it
is made of. Before creating a new environment, Karsk compares manifests: if an
identical environment already exists, nothing is created.

The name of the directory corresponds to the version of the main package `+` a
build ID (an integer). If a specific version is rebuilt to eg. fix an issue with
the specific build, the version stays the but the integer is incremented.

### Symlinks and aliases (`versions/`)

`versions` also contains the following symbolic links:

- `latest` points at the highest version present.
- `stable` points at `latest` by default, and can be pinned to a specific
  build via the `links` field in `config.yaml`.
- Automatic aliases are maintained per version prefix: `1.2` points at the
  newest `1.2.x` build, `1` at the newest `1.x`.

Because releases are just symlinks, promoting or rolling back a release is a
single atomic symlink update.

### Entrypoints (`bin/`)

`bin/` contains the configured entrypoints. Entrypoints use a wrapper that
resolves which version to execute at run time (`stable` by default, or can be
specified using the `--version` option). This is intended to be the user's main way of interacting with the deployed software.

## The staging area

[karsk build](commands/build.md) works in a local *staging area* (`./staging` by
default) so you can build and [interact](commands/enter.md) without touching the
destination. In it, per project and target architecture, are the same `store/`,
`versions/` and `bin/` layout as above, plus a shared `cache/` for downloaded
sources and other things.

## OCI engines

Karsk does all of its work inside containers. The *OCI engine* refers to any
program compatible with the [Open Container
Initiative](https://opencontainers.org/) specifications, commonly known as
[Podman](https://podman.io) or [Docker](https://docker.com)

While Podman is what we use in production, Docker is the industry standard and
is also supported. To use Docker instead of Podman, use `--engine docker` for
Karsk commands that use OCI.

## See also
