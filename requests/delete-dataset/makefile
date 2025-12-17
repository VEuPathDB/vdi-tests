ROOT_DIR  :=../..
CURL_UTIL := $(ROOT_DIR)/utils/curl.sh

DATASET_ID :=

DRY_RUN := 0
HEADERS := {}

__EXTRA_FLAGS :=
ifneq ($(DRY_RUN),0)
	__EXTRA_FLAGS += -d
endif

.PHONY: default
default:
	@exit 1

.PHONY: delete-dataset
delete-dataset:
	@if [ -z "$(DATASET_ID)" ]; then \
		echo -n "Dataset ID: " >&3; \
		read DATASET_ID; \
	else \
		DATASET_ID="$(DATASET_ID)"; \
	fi; \
	[ $(DRY_RUN) -eq 0 ] && echo "running delete request" >&3 || echo "generating curl command" >&3 ; \
	$(CURL_UTIL) -M DELETE -p "/datasets/$${DATASET_ID}" -h '$(HEADERS)' $(__EXTRA_FLAGS) 2>&3
