#!/bin/bash

if [ "$#" -ne 2 ]; then
  echo "USAGE: update_avro_from_aws <bucket> <prefix>"
  echo "EXAMPLE: update_avro_from_aws bucket-that-doesnt-exist/ prefix-that-doesnt-exist/"
  exit 1
fi

date="date=$(date -u '+%Y-%m-%d-%H')"
bucket=$1
prefix=$2

echo "INFO: Checking for avro schemas from ${date} in ${bucket}"

for path in $(aws s3 ls ${bucket}${prefix});
do
  if [[ $path != "" ]] && [[ $path != "PRE" ]]; then
    if [[ $path = "users"* ]]; then
      event_type=$(echo $path | sed 's/*//g;s/\///g')
      payloadpath=$(aws s3 ls "${bucket}${prefix}${path}${date}/" --recursive | sort | tail -n 1 | awk '{print $4}')
      if [[ $payloadpath == "" ]]; then
        echo "WARNING: Looks like we can't find anything for the current date ${date} in path ${path}, check the hour before."
        prev_date="date=$(date -u -v-60M '+%Y-%m-%d-%H')"
        payloadpath=$(aws s3 ls "${bucket}${prefix}${path}${prev_date}/" --recursive | sort | tail -n 1 | awk '{print $4}')
        if [[ $payloadpath == "" ]]; then
          echo "ERROR: Couldn't find data in ${prev_date} either. Exiting."
          exit 1
        fi
      fi
      aws s3 cp s3://${bucket}${payloadpath} Avro/${event_type}.avro
    fi
  fi
done
