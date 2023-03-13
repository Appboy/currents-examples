#!/bin/bash

dest=$1
bearer=$2

find sample-data/JSON \
     -type f \
     -name \*.json \
     -exec ./send_sample_event.sh ${dest} "{}" ${bearer} \
     \;

