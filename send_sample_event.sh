#!/bin/bash

# Any code, scripts, guides, written advice ("Scripts") provided by Braze herein are not, and shall not be, a component of the Braze Services nor the Braze SDK, as defined in Braze's Master Subscription Agreement. All Scripts are provided as-is, without any warranty of any kind, express or implied. In no event shall the authors or copyright holders any Script be liable for any claim, damages, or other liability arising from or in connection with the Script.

dest=$1
sample_file=$2
bearer=$3

if [[ ! -n ${dest} || ! -s ${sample_file} ]]; then
    echo "Usage: $0 URL Filename [Bearer Token]"
    exit 1
fi


auth_header=""
if [[ -n "$bearer" ]]; then
    auth_header="-H 'Authorization: Bearer ${bearer}'"
fi

curl \
    -X POST \
    -H 'Content-Type:application/json' \
     ${auth_header} \
    -d "`cat ${sample_file}`" \
    ${dest}

