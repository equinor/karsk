# karsk.context

`Context` is the object handed to test authors via the `karsk` pytest fixture.
It bundles a loaded configuration with the resolved package graph, the staging
and destination paths, and the container engine, and is what you use to inspect
packages and run programs inside the build environment.

::: karsk.context
