.PHONY: checks coverage format install lint test type 

install: requirements-dev.txt
	pip install -r requirements-dev.txt
	pip check

checks: format lint type ##@checks Run all code checks

coverage: ##@checks Create code coverage report
	coverage report -m --skip-covered

format: ##@checks Check code formatting
	black --check configue_cli

lint: ##@checks Run linting
	ruff check configue_cli

test: ##@checks Run all test suites across all environments
	coverage erase
	coverage run -m pytest tests/
	coverage xml -o coverage.xml
	$(MAKE) coverage

type: ##@checks Run type checking
	mypy configue_cli
