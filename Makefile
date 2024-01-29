.PHONY: test

test:
	poetry run coverage erase
	JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 poetry run coverage run -m pytest -svv itests
	poetry run coverage report --show-missing
