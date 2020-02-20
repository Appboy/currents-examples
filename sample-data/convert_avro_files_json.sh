#!/bin/bash
for file in Avro/*.avro
do
  echo $file
  avro-tools tojson "$file" > JSON/$(basename ${file%.*}).json
done
