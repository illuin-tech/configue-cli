.PHONY: checks coverage format install lint test type 

install: requirements-dev.txt
	pip install -r requirements-dev.txt
	pip check

checks: format lint type ##@checks Run all code checks

coverage: ##@checks Create code coverage report
	coverage report -m --skip-covered

format: ##@checks Check code formatting
	isort --check-only ${LINT_PATHS}
	black --check ${LINT_PATHS}

lint: ##@checks Run linting
	python -m pylint ${LINT_PATHS}

test: ##@checks Run all test suites across all environments
	coverage erase
	coverage run -m pytest tests/
	coverage xml -o coverage.xml
	$(MAKE) coverage

type: ##@checks Run type checking
	mypy ${TYPE_PATHS}
