#!/bin/bash

#Any code, scripts, guides, written advice ("Scripts") provided by Braze herein are not, and shall not be, a component of the Braze Services nor the Braze SDK, as defined in Braze's Master Subscription Agreement. All Scripts are provided as-is, without any warranty of any kind, express or implied. In no event shall the authors or copyright holders any Script be liable for any claim, damages, or other liability arising from or in connection with the Script.

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

