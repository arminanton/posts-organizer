.PHONY: test compile package

test:
	pytest

compile:
	python -m compileall src

package:
	python -m build
