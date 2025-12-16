MAKEFLAGS += --no-print-directory

.ONESHELL:

.PHONY: default
default:
	@echo no

HEADERS := {"Authorization":"Bearer ${VDI_AUTH_TOKEN}"}

.PHONY: create-dataset-biom-raw
create-dataset-biom-raw:  __env_test
	@RESULT_DIR="$$($(MAKE) -C requests/create-dataset create-biom-raw ROOT_DIR=${PWD} HEADERS='$(HEADERS)')"
	mv requests/create-dataset/$$RESULT_DIR .

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

.PHONY: __env_test
__env_test:
	@if [ -z "${VDI_AUTH_TOKEN}" ]; then
		echo
		echo
		echo "!!!   Missing required env var: VDI_AUTH_TOKEN"
		echo
		echo
		exit 1
	fi