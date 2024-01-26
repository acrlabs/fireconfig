.PHONY: test

test:
	poetry run coverage erase
	poetry run coverage run -m pytest -svv itests
	poetry run coverage report --show-missing
