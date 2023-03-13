#!/bin/bash -x

dest=$1
sample_file=$2
bearer=$3

auth_header=""
if [[ -n "$bearer" ]]; then
    auth_header="-H 'Authorization: Bearer ${bearer}'"
fi

curl \
    -X POST \
    -H 'Content-Type:application/json' \
     ${auth_header} \
    -d `cat ${sample_file}` \
    ${dest}

