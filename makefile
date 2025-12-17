MAKEFLAGS += --no-print-directory
DRY_RUN := 0
TEST_OUTPUT_DIR := test-outputs

HEADERS := {"Authorization":"Bearer ${VDI_AUTH_TOKEN}"}

.PHONY: default
default:
	@awk '{ \
	  if ($$1 == "#") { \
	    $$1=""; \
	    if (ht != "") { \
	      ht=ht "\n"; \
	    } \
	    if ($$2 == "|") { \
	      $$2=" "; \
	    } \
	    ht=ht "    " $$0; \
	  } else if ($$1 == ".PHONY:") { \
	    print "  \033[94m" $$2 "\033[39m\n" ht "\n"; \
	    ht="" \
	  } else {\
	    ht="" \
	  } \
	}' <(grep -B10 '.PHONY' makefile | grep -v '[═║@]\|default\|__' | grep -E '^[.#]|$$' | grep -v '_') | less

# Creates a new BIOM dataset
.PHONY: create-dataset-biom
create-dataset-biom: TEST_COMMAND := create-biom-raw
create-dataset-biom: __create_dataset_request

# Creates a new GeneList dataset for PlasmoDB
.PHONY: create-dataset-genelist-plasmo
create-dataset-genelist-plasmo: TEST_COMMAND := create-genelist-plasmo
create-dataset-genelist-plasmo: __create_dataset_request

# Creates a target dataset
.PHONY: delete-dataset
delete-dataset: TEST_DIR := requests/delete-dataset
delete-dataset: TEST_COMMAND := delete-dataset
delete-dataset: __test_request

# Prints visible user datasets to the console.
.PHONY: print-my-datasets
print-my-datasets:  __env_test
	@RESULT_DIR="$$($(MAKE) -C requests/list-my-datasets list-my-datasets ROOT_DIR=${PWD} HEADERS='$(HEADERS)' 3>&2 2>/dev/null)"
	if [ -n "$$RESULT_DIR" ]; then
		jq . requests/list-my-datasets/$$RESULT_DIR/body.txt
		rm -rf requests/list-my-datasets/$$RESULT_DIR
	else
		echo "NO RESULT"
		exit 1
	fi

# Gets a list of visible user datasets.
.PHONY: list-my-datasets
list-my-datasets: TEST_DIR := requests/list-my-datasets
list-my-datasets: TEST_COMMAND := list-my-datasets
list-my-datasets:  __test_request


.PHONY: __create_dataset_request
__create_dataset_request: TEST_DIR := requests/create-dataset
__create_dataset_request: __test_request


.PHONY: __test_request
__test_request: __env_test
	@RESULT_DIR="$$($(MAKE) -C $(TEST_DIR) $(TEST_COMMAND) ROOT_DIR=${PWD} HEADERS='$(HEADERS)' DRY_RUN=$(DRY_RUN) 3>&2 2>/dev/null)"; \
		if [ "$$?" -ne 0 ]; then echo "REQUEST FAILED!!!"; fi; \
		if [ -n "$$RESULT_DIR" ]; then mv $(TEST_DIR)/$$RESULT_DIR $(TEST_OUTPUT_DIR); echo "Output saved in $(TEST_OUTPUT_DIR)/$${RESULT_DIR}"; fi


.PHONY: __env_test
__env_test:
	@if [ -z "${VDI_AUTH_TOKEN}" ]; then \
		echo ; \
		echo ; \
		echo "!!!   Missing required env var: VDI_AUTH_TOKEN" ; \
		echo ; \
		echo ; \
		exit 1 ; \
	fi

$(TEST_OUTPUT_DIR):
	mkdir $(TEST_OUTPUT_DIR)