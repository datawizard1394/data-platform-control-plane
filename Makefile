.PHONY: help test check demo clean

PYTHON ?= python3
PYTHONPATH := src

help:
	@echo "make check  Compile modules and run dependency-free tests"
	@echo "make demo   Validate specs, create a dry-run plan, and compile manifests"
	@echo "make clean  Remove generated artifacts and bytecode"

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

check:
	$(PYTHON) -m compileall -q src tests
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

demo:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m control_plane \
		--spec-dir examples/specs --policy config/policy.json validate
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m control_plane \
		--spec-dir examples/specs --policy config/policy.json plan \
		--actual examples/actual_state.json
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m control_plane \
		--spec-dir examples/specs --policy config/policy.json compile \
		--output artifacts

clean:
	$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; shutil.rmtree('artifacts', ignore_errors=True)"

