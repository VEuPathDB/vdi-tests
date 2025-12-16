.ONESHELL:

.PHONY: default
default:
	@echo no

.PHONY: copy-env
copy-env:
	@cp request/client-env-example.json request/client.env.json

.PHONY: create-dataset-biom-raw
create-dataset-biom-raw:
	$(MAKE) -C requests/create-dataset create-biom-raw ROOT_DIR=${PWD}
