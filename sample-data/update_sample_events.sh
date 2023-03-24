#!/bin/bash
set -e

if [ "$#" -ne 2 ]; then
  echo "USAGE: update_sample_events.sh <bucket> <prefix>"
  echo "EXAMPLE: update_sample_events.sh bucket-that-doesnt-exist/ prefix-that-doesnt-exist/"
  exit 1
fi

./update_avro_from_aws.sh $1 $2 || exit 1
./convert_avro_files_json.sh

date=$(date '+%Y-%m-%d')
git checkout -b sample-data-update-${date}
git add .
git commit -m "Updated sample-data from AWS"

gh pr create -t "Update sample-data" -b "Updating sample-data from ${date}"
