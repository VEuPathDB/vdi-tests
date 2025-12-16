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
