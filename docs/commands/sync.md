# karsk sync

## NAME
karsk\-sync - Synchronise a Karsk environment

## SYNOPSIS
**karsk sync** [*options*] *config* *areas*

## DESCRIPTION
**karsk sync** replicates the *destination* directory (as specified in the *config*) from localhost to the same path on every host listed in the *areas* file, using rsync over SSH.

The *areas* file is a YAML file with a top-level `areas:` list of `name`/`host`
entries. For example:

```yaml
areas:
  - name: Bergen
    host: be-top01.equinor.com
  - name: Stavanger
    host: st-top01.equinor.com
```

## OPTIONS

--8<-- "docs/commands/common-options.md:staging"

## NOTES

Unlike to [**karsk install**](./karsk-install), this command will copy the destination path as-is, ensuring that the deployment is identical to this system's destination path across all sync areas. As such, it is required to *install* before *sync*.

## SEE ALSO
