.ONESHELL:

.PHONY: default
default:
	@echo no

.PHONY: copy-env
copy-env:
	@cp request/client-env-example.json request/client.env.json

