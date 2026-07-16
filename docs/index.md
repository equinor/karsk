# Karsk

--8<-- "README.md:intro"

See [Concepts](concepts.md) for how Karsk achieves this.

## Example

The following is a simple example, showing off the configuration for building a
hello-world application.

```dockerfile
# Containerfile
--8<-- "examples/hello_world/Containerfile"
```

```yaml
# config.yaml
--8<-- "examples/hello_world/config.yaml"
```

Build it and try it out in an interactive session, where the built environment
is mounted at its destination paths:

```console
$ karsk build config.yaml
Building hello-1.0.0...
...
Created symlink: staging/hello/x86_64-unknown-linux/versions/latest -> 1.0.0+1
Created symlink: staging/hello/x86_64-unknown-linux/versions/stable -> latest
Creating entrypoints:
- bin/binary.sh

$ karsk enter config.yaml
(Karsk 🥃) $ binary.sh --version
Version 1.0.0
running with args: --version
```
