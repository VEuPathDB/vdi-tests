ROOT_DIR :=../..
CUR_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

CURL_UTIL := $(ROOT_DIR)/utils/curl.sh

DRY_RUN := 0
HEADERS := $(shell echo '$(HEADERS)' | jq '.["Content-Type"] = "application/json"')

INPUT_FILE :=

__EXTRA_FLAGS :=

ifneq ($(DRY_RUN),0)
	__EXTRA_FLAGS += -D
endif


.PHONY: default
default:
	@exit 1


# ╔══════════════════════════════════════════════════════════════════════════╗ #
# ║  Request Definitions                                                     ║ #
# ╚══════════════════════════════════════════════════════════════════════════╝ #

.PHONY: make-public
make-public: INPUT_FILE := $(CUR_DIR)/make-public.json
make-public: __run-request



# ╔══════════════════════════════════════════════════════════════════════════╗ #
# ║  Internal Helper Targets                                                 ║ #
# ╚══════════════════════════════════════════════════════════════════════════╝ #

.PHONY: __run-create
__run-request:
	@if [ -z "$(DATASET_ID)" ]; then \
		echo -n "Dataset ID: " >&3; \
		read DATASET_ID; \
	else \
		DATASET_ID="$(DATASET_ID)"; \
	fi; \
	[ $(DRY_RUN) -eq 0 ] && echo "running patch request" >&2 || echo "generating curl command" >&2; \
	$(CURL_UTIL) -M PATCH -p "/datasets/$${DATASET_ID}" -h '$(HEADERS)' -d '@$(INPUT_FILE)' $(__EXTRA_FLAGS) 2>&3
