.ONESHELL:
ROOT_DIR :=../..
HEADERS := {"Authorization":"Bearer ${VDI_AUTH_TOKEN}"}
CUR_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

CURL_UTIL := $(ROOT_DIR)/utils/curl.sh
FORM_UTIL := $(ROOT_DIR)/utils/form-files.sh

BIOM_DIR := $(CUR_DIR)/biom

.PHONY: default
default:
	@exit 1

.PHONY: create-biom-raw
create-biom-raw: FORM_FIELDS := $(shell $(FORM_UTIL) -e "$(BIOM_DIR)/request-meta.json" -d "$(BIOM_DIR)/data.biom")
create-biom-raw:
	@echo "Create new dataset from unpacked BIOM file"
	RESULT_DIR=$$($(CURL_UTIL) \
		-M POST \
		-p "/datasets" \
		-h '$(HEADERS)' \
		-f '$(FORM_FIELDS)')
	mv $$RESULT_DIR $(ROOT_DIR)