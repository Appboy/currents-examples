#!/bin/bash

# Any code, scripts, guides, recommendations, and/or written advice (generally, "Scripts") provided by Braze herein are not, and shall not be considered a component of the Braze Services nor the Braze SDK, as defined in Braze's Main Subscription Agreement. All Scripts are provided as-is, without any warranty of any kind, express or implied. In no event shall Braze be liable for any claim, damages, or other liability arising from or in connection with any such Script.

dest=$1
bearer=$2

if [[ ! -n ${dest} ]]; then
    echo "Usage: $0 URL [Bearer Token]"
    exit 1
fi


find sample-data/JSON \
     -type f \
     -name \*.json \
     -exec ./send_sample_event.sh ${dest} "{}" ${bearer} \
     \;

