.ONESHELL:
ROOT_DIR :=../..
CUR_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

CURL_UTIL := $(ROOT_DIR)/utils/curl.sh

.PHONY: default
default:
	@exit 1

.PHONY: list-my-datasets
list-my-datasets:
	@$(CURL_UTIL) -p "/datasets" -h '$(HEADERS)'

.PHONY: list-shared-datasets
list-shared-datasets:
	@$(CURL_UTIL) -p "/datasets" -h '$(HEADERS)' -q '?ownership=shared'

.PHONY: list-shared-datasets
list-shared-datasets:
	@$(CURL_UTIL) -p "/datasets" -h '$(HEADERS)' -q '?ownership=shared'
