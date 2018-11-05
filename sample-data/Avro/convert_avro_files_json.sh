#!/bin/bash
for file in *.avro
do
  echo $file
  avro-tools tojson "$file" >> avro_json_files/${file}.json
done
