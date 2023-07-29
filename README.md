# fireconfig

FireConfig is a (prototype of) a Python-based configuration-as-code library for generating Kubernetes manifests built on
top of [cdk8s](https://cdk8s.io).  It is _extremely_ alpha code, so use at your own risk!  If this seems cool, I'd
welcome pull requests to make it better!

## Developing

It is highly recommended that you install [pre-commit](https://pre-commit.com); this will run useful checks before you
push anything to GitHub.  To set up the hooks in this repo, run `pre-commit install`.

This project uses [poetry](https://python-poetry.org) to manage dependencies.  You can set up for development by running
`poetry install`, and for tests/mypy/etc, you can run `poetry shell` to enter the virtualenv.

There are currently no tests.  Maybe someday I will add some.
