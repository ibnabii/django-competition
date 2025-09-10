# Variables for documentation (npm) tools
DOCS_DIR=docs_src
ANTORA_CLI=@antora/cli
ANTORA_GEN=@antora/site-generator-default

.PHONY: help test lint build-docs clean-docs

help:
	@echo Targets:
#    @echo "  make test        - Run Django tests"
#    @echo "  make lint        - Run flake8 linting"
	@echo Docs:
	@echo   make antora-install	- Install Antora (npm docs engine)
	@echo   make build-docs  	- Build documentation
	@echo   make clean-docs  	- Clean documentation artifacts

antora-install:
    # Installs Antora CLI & site generator locally
	cd $(DOCS_DIR) && npm install $(ANTORA_CLI) $(ANTORA_GEN)

# TODO: test
#test:
#    python manage.py test

lint:
# TODO: isort, split requirements to dev/target
	flake8 .
	isort .

build-docs: antora-install
	cd $(DOCS_DIR) && npx antora antora-playbook.yml

clean-docs:
	rm -rf $(DOCS_DIR)/build/
	rm -rf $(DOCS_DIR)/node_modules/