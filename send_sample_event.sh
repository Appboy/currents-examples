#!/bin/bash

# Any code, scripts, guides, recommendations, and/or written advice (generally, "Scripts") provided by Braze herein are not, and shall not be considered a component of the Braze Services nor the Braze SDK, as defined in Braze's Main Subscription Agreement. All Scripts are provided as-is, without any warranty of any kind, express or implied. In no event shall Braze be liable for any claim, damages, or other liability arising from or in connection with any such Script.

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

