# 🔥Config

🔥Config is a (prototype of) a Python-based configuration-as-code library for generating Kubernetes manifests built on
top of [cdk8s](https://cdk8s.io).  It is _extremely_ alpha code, so use at your own risk!  If this seems cool, I'd
welcome pull requests to make it better!  There is currently no stable API, things may change significantly between
versions.

## Usage

🔥Config is designed on the [builder pattern](https://en.wikipedia.org/wiki/Builder_pattern).  You construct a base
Kubernetes object with all the required fields, and then can configure it using chained method calls.  Here is an
example to construct a deployment object with a single container:

```
import fireconfig as fire
from cdk8s import App, Chart
from constructs import Construct

listen_port = 8080

class Nginx(Chart):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        container = fire.ContainerBuilder(
            name='nginx',
            image='nginx:latest',
            command='nginx',
        ).with_ports(listen_port)

        deployment = fire.DeploymentBuilder(
            namespace="default",
            selector={"app": "nginx"},
        ).with_service(listen_port).with_containers(container).build(self)
```

This creates a Kubernetes manifest for an nginx pod and a service listening on port 8080.

## Developing

It is highly recommended that you install [pre-commit](https://pre-commit.com); this will run useful checks before you
push anything to GitHub.  To set up the hooks in this repo, run `pre-commit install`.

This project uses [poetry](https://python-poetry.org) to manage dependencies.  You can set up for development by running
`poetry install`, and for tests/mypy/etc, you can run `poetry shell` to enter the virtualenv.

There are currently no tests.  Maybe someday I will add some.
