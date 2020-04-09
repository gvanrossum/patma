# Assume Python 3.8

all: mypy test

mypy:
	mypy *.py

test:
	pytest
