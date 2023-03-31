-include .env

PROJECT_NAME=configue-cli
PIP_COMPILE=pip-compile pyproject.toml -q --resolver=backtracking --no-emit-index-url
LINT_PATHS=configue_cli/
TYPE_PATHS=configue_cli/

HELP_FUN = \
	%help; \
	while(<>) { \
	push @{$$help{$$2 // 'options'}}, [$$1, $$3] if(/^([a-z0-9_-]+):.*\#\#(?:@(\w+))?\s(.*)$$/) }; \
	print "${PROJECT_NAME} developer tool\n\n"; \
	print "\033[1mUSAGE\n\033[0m  make <target>\n\n\n"; \
	print "\033[1mAVAILABLE TARGETS\n\033[0m\n"; \
	for (keys %help) { \
		print "  \033[1m$$_\n\033[0m"; $$sep = " " x (20 - length $$_->[0]); \
		printf("    \033[36m%-20s\033[0m %s\n", $$_->[0], $$_->[1]) for @{$$help{$$_}}; \
		print "\n"; }

.DEFAULT_GOAL := help
.PHONY: \
	clean \
	clean-all \
	checks \
	coverage \
	format \
	help \
	install \
	lint \
	test \
	type 


################################
#        Miscellaneous         #
################################

help: ##@miscellaneous Show this help
	@perl -e '$(HELP_FUN)' $(MAKEFILE_LIST)

clean: ##@miscellaneous Clean local repository
	rm -rf .cache
	rm -rf .tox
	rm -f coverage.xml
	rm -f .coverage
	rm -rf .pytest_cache
	rm -rf **/__pycache__
	rm -rf dist/*
	rm -rf coverage
	rm -rf docs/build
	rm -rf dist/
	rm -rf build/
	rm -f *.so
	rm -rf __pycache__/
	rm -rf configue_cli.egg-info/

check-clean:
	@echo "Are you sure? [y/N] " && read ans && [ $${ans:-N} = y ]

clean-all: check-clean ##@miscellaneous Remove all intermediary artifacts
	$(MAKE) clean


################################
#         Development          #
################################

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
