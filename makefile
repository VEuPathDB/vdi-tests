MAKEFLAGS += --no-print-directory
DRY_RUN := 0
TEST_OUTPUT_DIR := test-outputs

HEADERS := {"Authorization":"Bearer ${VDI_AUTH_TOKEN}"}

MAKE_REQUEST_COMMAND = $(MAKE) -C $(TEST_DIR) $(TEST_COMMAND) ROOT_DIR=${PWD} HEADERS='$(HEADERS)' DRY_RUN=$(DRY_RUN) 3>&2 2>/dev/null


# ╔══════════════════════════════════════════════════════════════════════════╗ #
# ║  Project Meta & Maintenance Targets                                      ║ #
# ╚══════════════════════════════════════════════════════════════════════════╝ #

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

# Deletes all test result sub directories under ./test-outputs
.PHONY: clear-test-results
clear-test-results:
	@find test-outputs/* -maxdepth 1 -type d -name 'test-*' \
		| grep '/test-[0-9]\+$$' \
		| while read dirpath; do \
			echo "deleting test output $${dirpath}"; \
			rm -rf "$${dirpath}"; \
		done


# ╔══════════════════════════════════════════════════════════════════════════╗ #
# ║  Dataset Information Requests                                            ║ #
# ╚══════════════════════════════════════════════════════════════════════════╝ #

# Prints visible user datasets to the console as JSONs.
.PHONY: print-my-datasets
print-my-datasets: TEST_DIR := requests/list-my-datasets
print-my-datasets: TEST_COMMAND := list-my-datasets
print-my-datasets:  __env_test
	@RESULT_DIR="$$($(MAKE_REQUEST_COMMAND))"; \
	if [ "$$?" -ne 0 ]; then echo "REQUEST FAILED!!!"; fi; \
	if [ -n "$${RESULT_DIR}" ]; then \
		STATUS_CODE_FILE="$(TEST_DIR)/$${RESULT_DIR}/status.txt"; \
		STATUS_CODE_VALUE="$$([ -f "$${STATUS_CODE_FILE}" ] && cat "$${STATUS_CODE_FILE}" || echo -n 'unknown')"; \
		if [ $${STATUS_CODE_VALUE} = '200' ]; then \
			jq . $(TEST_DIR)/$${RESULT_DIR}/body.txt; \
			rm -rf $(TEST_DIR)/$${RESULT_DIR}; \
		else \
			mv $(TEST_DIR)/$${RESULT_DIR} $(TEST_OUTPUT_DIR); \
			echo "response status: $${STATUS_CODE_VALUE}"; \
			echo ""; \
			echo "output saved in $(TEST_OUTPUT_DIR)/$${RESULT_DIR}"; \
		fi; \
	else \
		echo "NO RESULT"; \
		exit 1; \
	fi

# Gets a list of visible user datasets.
.PHONY: list-my-datasets
list-my-datasets: TEST_DIR := requests/list-my-datasets
list-my-datasets: TEST_COMMAND := list-my-datasets
list-my-datasets:  __test_request


# ╔══════════════════════════════════════════════════════════════════════════╗ #
# ║  Dataset Creation Requests                                               ║ #
# ╚══════════════════════════════════════════════════════════════════════════╝ #

# Creates a new BIOM dataset
.PHONY: create-biom-dataset
create-biom-dataset: TEST_COMMAND := create-biom-raw
create-biom-dataset: __create_dataset_request

# Creates a new GeneList dataset for PlasmoDB
.PHONY: create-genelist-plasmo-dataset
create-genelist-plasmo-dataset: TEST_COMMAND := create-genelist-plasmo
create-genelist-plasmo-dataset: __create_dataset_request


# ╔══════════════════════════════════════════════════════════════════════════╗ #
# ║  Dataset Alteration Requests                                             ║ #
# ╚══════════════════════════════════════════════════════════════════════════╝ #

# Deletes a target dataset
#
# If the `DATASET_ID` variable is set, that dataset ID will be used for the
# delete request.  If not provided, the caller will be prompted for the dataset
# ID interactively.
.PHONY: delete-dataset
delete-dataset: TEST_DIR := requests/delete-dataset
delete-dataset: TEST_COMMAND := delete-dataset
delete-dataset: __test_request


.PHONY: patch-dataset-make-public
patch-dataset-make-public: TEST_DIR := requests/patch-dataset
patch-dataset-make-public: TEST_COMMAND := make-public
patch-dataset-make-public: __test_request



# ╔══════════════════════════════════════════════════════════════════════════╗ #
# ║  Needlessly Complicated Internal Junk                                    ║ #
# ╚══════════════════════════════════════════════════════════════════════════╝ #

.PHONY: __create_dataset_request
__create_dataset_request: TEST_DIR := requests/create-dataset
__create_dataset_request: __env_test
	@RESULT_DIR="$$($(MAKE_REQUEST_COMMAND))"; \
	if [ "$$?" -ne 0 ]; then \
		echo "REQUEST FAILED!!!"; \
	elif [ $(DRY_RUN) -ne 0 ]; then \
		mv $(TEST_DIR)/$$RESULT_DIR $(TEST_OUTPUT_DIR); \
		echo "Output saved in $(TEST_OUTPUT_DIR)/$${RESULT_DIR}/curl-command.sh"; \
	else \
		mv $(TEST_DIR)/$${RESULT_DIR} $(TEST_OUTPUT_DIR); \
		STATUS_CODE_FILE="$(TEST_OUTPUT_DIR)/$${RESULT_DIR}/status.txt"; \
		STATUS_CODE_VALUE="$$([ -f "$${STATUS_CODE_FILE}" ] && cat "$${STATUS_CODE_FILE}" || echo -n 'xxx')"; \
		case $${STATUS_CODE_VALUE} in \
			202) \
				jq -r .datasetId $(TEST_OUTPUT_DIR)/$${RESULT_DIR}/body.txt; \
				exit 0; \
				;; \
			xxx) \
				echo ""; \
				tput setaf 196; \
				echo "    unknown error occurred"; \
				tput sgr0; \
				echo ""; \
				;; \
			*) \
				echo ""; \
				tput setaf 196; \
				echo "    service responded with $${STATUS_CODE_VALUE}"; \
				tput sgr0; \
				echo ""; \
				;; \
		esac; \
		echo "output saved in $(TEST_OUTPUT_DIR)/$${RESULT_DIR}"; \
	fi

.PHONY: __test_request
__test_request: __env_test
	@RESULT_DIR="$$($(MAKE_REQUEST_COMMAND))"; \
	if [ "$$?" -ne 0 ]; then echo "REQUEST FAILED!!!"; fi; \
	if [ -n "$${RESULT_DIR}" ]; then \
		mv $(TEST_DIR)/$${RESULT_DIR} $(TEST_OUTPUT_DIR); \
		STATUS_CODE_FILE="$(TEST_OUTPUT_DIR)/$${RESULT_DIR}/status.txt"; \
		STATUS_CODE_VALUE="$$([ -f "$${STATUS_CODE_FILE}" ] && cat "$${STATUS_CODE_FILE}" || echo -n 'unknown')"; \
		echo "response status: $${STATUS_CODE_VALUE}"; \
		echo ""; \
		echo "output saved in $(TEST_OUTPUT_DIR)/$${RESULT_DIR}"; \
	fi


.PHONY: __env_test
__env_test:
	@if [ -z "${VDI_AUTH_TOKEN}" ]; then \
		echo ; \
		echo ; \
		tput setaf 196; \
		echo "    Missing required env var: VDI_AUTH_TOKEN" ; \
		tput sgr0; \
		echo ; \
		echo ; \
		exit 1 ; \
	fi

$(TEST_OUTPUT_DIR):
	mkdir $(TEST_OUTPUT_DIR)
