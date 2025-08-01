#########
# BUILD #
#########
.PHONY: develop build install

develop:  ## install dependencies and build library
	uv pip install -e .[develop]

build:  ## build the python library
	python -m build -n

install:  ## install library
	uv pip install .

#########
# LINTS #
#########
.PHONY: lint lints fix format

lint:  ## run python linter with ruff
	python -m ruff check voidorchestra
	python -m ruff format --check voidorchestra

# Alias
lints: lint

fix:  ## fix python formatting with ruff
	python -m ruff check --fix voidorchestra
	python -m ruff format voidorchestra

# alias
format: fix

################
# Other Checks #
################
.PHONY: check-manifest checks check

check-manifest:  ## check python sdist manifest with check-manifest
	check-manifest -v

checks: check-manifest

# Alias
check: checks

#########
# TESTS #
#########
.PHONY: test coverage tests

test:  ## run python tests
	python -m pytest -v voidorchestra/tests

coverage:  ## run tests and collect test coverage
	python -m pytest -v voidorchestra/tests --cov=voidorchestra --cov-report term-missing --cov-report xml

# Alias
tests: test

###########
# VERSION #
###########
.PHONY: show-version patch minor major

show-version:  ## show current library version
	@bump-my-version show current_version

patch:  ## bump a patch version
	@bump-my-version bump patch

minor:  ## bump a minor version
	@bump-my-version bump minor

major:  ## bump a major version
	@bump-my-version bump major

########
# DIST #
########
.PHONY: dist dist-build dist-sdist dist-local-wheel publish

dist-build:  # build python dists
	python -m build -w -s

dist-check:  ## run python dist checker with twine
	python -m twine check dist/*

dist: clean dist-build dist-check  ## build all dists

publish: dist  # publish python assets

#########
# CLEAN #
#########
.PHONY: deep-clean clean

deep-clean: ## clean everything from the repository
	git clean -fdx

clean: ## clean the repository
	rm -rf .coverage coverage cover htmlcov logs build dist *.egg-info

############################################################################################

.PHONY: help

# Thanks to Francoise at marmelab.com for this
.DEFAULT_GOAL := help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

print-%:
	@echo '$*=$($*)'

############################################################################################
# Project Commands
############################################################################################

database:
	uv run void-orchestra --debug delete database
	uv run void-orchestra --debug delete sonifications --hard
	uv run void-orchestra --debug init database

fixtures:
	uv run void-orchestra --debug delete soundfonts
	uv run void-orchestra --debug delete profiles
	uv run void-orchestra --debug input soundfonts
	uv run void-orchestra --debug input profiles

synthetic:
	uv run scripts/generate_synthetic_lightcurves.py

sonifications:
	uv run void-orchestra create sonifications --regenerate
