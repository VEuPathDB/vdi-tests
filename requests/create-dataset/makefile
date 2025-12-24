ROOT_DIR :=../..
CUR_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

CURL_UTIL := $(ROOT_DIR)/utils/curl.sh
FORM_UTIL := $(ROOT_DIR)/utils/form-files.sh

DRY_RUN := 0
HEADERS := {}

__EXTRA_FLAGS :=

ifneq ($(DRY_RUN),0)
	__EXTRA_FLAGS += -D
endif

.PHONY: default
default:
	@exit 1

# ╔══════════════════════════════════════════════════════════════════════════╗ #
# ║  BIOM Plugin Dataset Creation Requests                                   ║ #
# ╚══════════════════════════════════════════════════════════════════════════╝ #

BIOM_DIR := $(CUR_DIR)/biom

.PHONY: create-biom-raw
create-biom-raw: FORM_FIELDS := $(shell $(FORM_UTIL) -e "$(BIOM_DIR)/request-meta.json" -d "$(BIOM_DIR)/data.biom")
create-biom-raw: __run-create


# ╔══════════════════════════════════════════════════════════════════════════╗ #
# ║  GeneList Plugin Dataset Creation Requests                               ║ #
# ╚══════════════════════════════════════════════════════════════════════════╝ #

GENELIST_DIR := $(CUR_DIR)/genelist

.PHONY: create-genelist-plasmo
create-genelist-plasmo: FORM_FIELDS := $(shell $(FORM_UTIL) -e "$(GENELIST_DIR)/plasmo-01/meta.json" -d "$(GENELIST_DIR)/plasmo-01/data.zip")
create-genelist-plasmo: __run-create


# ╔══════════════════════════════════════════════════════════════════════════╗ #
# ║  Internal Helper Targets                                                 ║ #
# ╚══════════════════════════════════════════════════════════════════════════╝ #

.PHONY: __run-create
__run-create:
	@[ $(DRY_RUN) -eq 0 ] && echo "running create request" >&2 || echo "generating curl command" >&2
	@$(CURL_UTIL) -M POST -p "/datasets" -h '$(HEADERS)' -f '$(FORM_FIELDS)' $(__EXTRA_FLAGS) 2>&3
