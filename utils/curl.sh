#!/usr/bin/env sh

declare vdiHost="http://localhost:8081"
declare httpMethod="GET"
declare endpointPath=""
declare httpHeaders=""
declare formInputs=""
declare dataInput=""
declare -i dryRun=0

parseMap() {
  cat > jq.filter <<EOF
. as \$ROOT | keys[] | . as \$KEY | \$ROOT[\$KEY] | if type=="array" then .[] else . end | "$1 '" + \$KEY + "$2" + . + "'"
EOF
  jq -rf jq.filter <<< "$3"
  rm jq.filter
}

buildMapLines() {
  local output=''
  while read line; do
    output+="$(printf ' \\\n  %s' "${line}")"
  done < <(parseMap "$1" "$2" "$3")
  echo "$output"
}

buildMultilineCommand() {
  local output="curl -isX${1}"

  # Headers
  if [ -n "${2}" ]; then
    output+="$(buildMapLines "-H" ": " "${2}")"
  fi

  # Form Fields
  if [ -n "${3}" ]; then
    output+="$(buildMapLines "-F" "=" "${3}")"
  fi

  # Data Input
  if [ -n "${4}" ]; then
    output+="$(printf ' \\\n  -d %s' "'${4}'")"
  fi

  output+="$(printf ' \\\n  %s' "${5}")"

  echo "$output"
}

while getopts ':H:M:h:f:dp:q:' option; do
  case $option in
    H)
      vdiHost="${OPTARG}"
      ;;
    M)
      httpMethod="${OPTARG}"
      ;;
    h)
      httpHeaders="${OPTARG}"
      ;;
    f)
      formInputs="${OPTARG}"
      ;;
    d)
      dataInput="${OPTARG}"
      ;;
    D)
      dryRun=1
      ;;
    p)
      endpointPath="${OPTARG}"
      ;;
    q)
      queryString="${OPTARG}"
      ;;
  esac
done

declare -r timestamp=$(date +%s%3N)
declare -r resultDir=test-$timestamp

mkdir $resultDir
echo $resultDir

buildMultilineCommand \
  "${httpMethod}" \
  "${httpHeaders}" \
  "${formInputs}" \
  "${dataInput}" \
  "${vdiHost}${endpointPath}${queryString}" \
  > ${resultDir}/curl-command.sh

chmod +x ${resultDir}/curl-command.sh

if [ $dryRun -eq 1 ]; then
  exit 0
else
  ${resultDir}/curl-command.sh > ${resultDir}/full-response.txt || exit 1
fi

cd ${resultDir}

head -n1 full-response.txt | sed 's/.\+ \([0-9]\+\) .\+/\1/' | tr -d '\n' > status.txt
sed -n '/^\r/q;p' full-response.txt | sed '1d' > headers.txt
sed '1,/^\r/d' full-response.txt > body.txt
