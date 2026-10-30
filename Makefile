.PHONY: run test

run:
	PYTHONPATH=src python3 -m depviz

test:
	python3 -m unittest discover -s tests -t . -v
