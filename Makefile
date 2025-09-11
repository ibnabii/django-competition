# Variables for documentation (npm) tools
DOCS_DIR=docs_src
ANTORA_CLI=@antora/cli
ANTORA_GEN=@antora/site-generator-default
DOC_DIRS = root-index user_guide developer_guide admin_guide
COMMIT_MSG = "Update docs"

.PHONY: help test lint build-docs clean-docs
.PHONY: requirements requirements-dev test-coverage
help:
	@echo Targets:
#    @echo "  make test        - Run Django tests"
#    @echo "  make lint        - Run flake8 linting"
	@echo Docs:
	@echo   make antora-install	- Install Antora (npm docs engine)
	@echo   make commit-docs  	- Commit latest version of docs to local repos
	@echo   make build-docs  	- Build documentation
	@echo   make clean-docs  	- Clean documentation artifacts
	@echo Dev-env setup:
	@echo   make requirements		- install prod python packages
	@echo   make requirements-dev	- install dev python packages


antora-install:
    # Installs Antora CLI & site generator locally
	cd $(DOCS_DIR) && npm install $(ANTORA_CLI) $(ANTORA_GEN) asciidoctor-kroki


# commit all docs into it's respective git repos
commit-docs:
	cd $(DOCS_DIR) & \
	@for %%d in ($(DOC_DIRS)) do ( \
		echo Committing in %%d... & \
		cd %%d & \
		git add . & \
		echo Added to git & \
		git commit -m "$(COMMIT_MSG)" & \
		echo Commited to git & \
		cd .. \
    )

# TODO: test
#test:
#    python manage.py test

lint:
# TODO: isort, split requirements to dev/target
	flake8 .
	isort .

build-docs: antora-install
	cd $(DOCS_DIR) && npx antora antora-playbook.yml

clean-docs-build:
	if exist $(DOCS_DIR)\build rmdir /S /Q $(DOCS_DIR)\build

clean-docs: clean-docs-build
	if exist $(DOCS_DIR)\node_modules rmdir /S /Q $(DOCS_DIR)\node_modules


# requirements
requirements:
	pip install -r requirements/base.txt

requirements-dev:
	pip install -r requirements/local.txt

# tests
test-coverage:
	pytest --cov=. --cov-report html