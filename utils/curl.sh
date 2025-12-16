#!/usr/bin/env sh

declare vdiHost="http://localhost:8080"
declare httpMethod="GET"
declare endpointPath=""
declare httpHeaders=""
declare formInputs=""
declare -i dryRun=0

parseMap() {
  cat > jq.filter <<EOF
. as \$ROOT | keys[] | . as \$KEY | \$ROOT[\$KEY] | if type=="array" then .[] else . end | "$1 '" + \$KEY + "$2" + . + "'"
EOF
  jq -rf jq.filter <<< "$3"
  rm jq.filter
}

buildMapLines() {
  local output=""
  while read line; do
    output+="$(printf '%s \\\n' "${line}")"
  done < <(parseMap "$1" "$2" "$3")
  echo $output
}

while getopts ':H:M:h:f:dp:q:' option; do
  case $option in
    H)
      vdiHost="$OPTARG"
      ;;
    M)
      httpMethod="$OPTARG"
      ;;
    h)
      httpHeaders=$(buildMapLines "-H" ": " "$OPTARG")
      ;;
    f)
      formInputs=$(buildMapLines "-F" "=" "$OPTARG")
      ;;
    d)
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
declare -r resultDir=curl-$timestamp

mkdir $resultDir

cat > ${resultDir}/curl-command.sh <<EOF
curl -isX${httpMethod} \\
  ${httpHeaders}
  ${formInputs}
  "${vdiHost}${endpointPath}${VDI_QUERY_PARAMS}"
EOF
chmod +x ${resultDir}/curl-command.sh

if [ $dryRun -eq 1 ]; then
  echo $resultDir
  exit 0
else
  ${resultDir}/curl-command.sh > ${resultDir}/full-response.txt || exit 1
fi

cd ${resultDir}

head -n1 full-response.txt | sed 's/.\+ \([0-9]\+\) .\+/\1/' | tr -d '\n' > status.txt
sed -n '/^\r/q;p' full-response.txt | sed '1d' > headers.txt
sed '1,/^\r/d' full-response.txt > body.txt

echo $resultDir
