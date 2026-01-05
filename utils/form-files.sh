#!/usr/bin/env sh

declare metaDetails=""
declare -a dataFiles=()
declare -a propFiles=()
declare -a docFiles=()

while getopts ':e:d:p:x:' option; do
  case $option in
    e)
      metaDetails="${OPTARG}"
      ;;
    d)
      dataFiles+=("${OPTARG}")
      ;;
    p)
      propFiles+=("${OPTARG}")
      ;;
    x)
      docFiles+=("${OPTARG}")
      ;;
  esac
done

declare jsonValue="{}"

if [ -n "${metaDetails}" ]; then
  jsonValue=$(jq -c '.details = "@'"${metaDetails}"'"' <<< "${jsonValue}")
fi

if [ "${#dataFiles[@]}" -gt 0 ]; then
  for f in "${dataFiles[@]}"; do
    jsonValue=$(jq -c '.dataFile += ["@'"${f}"'"]' <<< "${jsonValue}")
  done
fi

if [ "${#propFiles[@]}" -gt 0 ]; then
  for f in "${propFiles[@]}"; do
    jsonValue=$(jq -c '.dataPropertiesFile += ["@'"${f}"'"]' <<< "${jsonValue}")
  done
fi

if [ "${#docFiles[@]}" -gt 0 ]; then
  for f in "${docFiles[@]}"; do
    jsonValue=$(jq -c '.docFile += ["@'"${f}"'"]' <<< "${jsonValue}")
  done
fi

echo "${jsonValue}"