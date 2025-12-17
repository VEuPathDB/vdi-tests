MAKEFLAGS += --no-print-directory
DRY_RUN := 0

.PHONY: default
default:
	@echo no

HEADERS := {"Authorization":"Bearer ${VDI_AUTH_TOKEN}"}

.PHONY: create-dataset-biom-raw
create-dataset-biom-raw: CREATE_COMMAND := create-biom-raw
create-dataset-biom-raw: __create_dataset_request
	@RESULT_DIR="$$($(MAKE) -C requests/create-dataset  ROOT_DIR=${PWD} HEADERS='$(HEADERS)' DRY_RUN=$(DRY_RUN))"; \
		if [ "$$?" -ne 0 ]; then echo "REQUEST FAILED!!!"; fi; \
		if [ -n "$$RESULT_DIR" ]; then mv requests/create-dataset/$$RESULT_DIR .; fi

.PHONY: create-dataset-genelist-plasmo-raw
create-dataset-genelist-plasmo-raw: CREATE_COMMAND := create-genelist-plasmo
create-dataset-genelist-plasmo-raw: __create_dataset_request

.PHONY: print-my-datasets
print-my-datasets:  __env_test
	@RESULT_DIR="$$($(MAKE) -C requests/list-my-datasets list-my-datasets ROOT_DIR=${PWD} HEADERS='$(HEADERS)')"
	if [ -n "$$RESULT_DIR" ]; then
		jq . requests/list-my-datasets/$$RESULT_DIR/body.txt
		rm -rf requests/list-my-datasets/$$RESULT_DIR
	else
		echo "NO RESULT"
		exit 1
	fi

.PHONY: get-my-datasets
get-my-datasets:  __env_test
	@RESULT_DIR="$$($(MAKE) -C requests/list-my-datasets list-my-datasets ROOT_DIR=${PWD} HEADERS='$(HEADERS)')"
	if [ -n "$$RESULT_DIR" ]; then
		mv requests/list-my-datasets/$$RESULT_DIR .
	else
		echo "NO RESULT"
		exit 1
	fi


.PHONY: __create_dataset_request
__create_dataset_request: __env_test
	@RESULT_DIR="$$($(MAKE) -C requests/create-dataset $(CREATE_COMMAND) ROOT_DIR=${PWD} HEADERS='$(HEADERS)' DRY_RUN=$(DRY_RUN) 3>&2 2>/dev/null)"; \
		if [ "$$?" -ne 0 ]; then echo "REQUEST FAILED!!!"; fi; \
		if [ -n "$$RESULT_DIR" ]; then mv requests/create-dataset/$$RESULT_DIR .; echo "Output saved in $${RESULT_DIR}/"; fi


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