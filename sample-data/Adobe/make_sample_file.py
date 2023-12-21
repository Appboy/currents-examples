#!/usr/bin/env python

import sys
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAMPLE_DATA_DIR = HERE.parent
CUSTOM_HTTP_DIR = SAMPLE_DATA_DIR / 'Custom HTTP'

OUTPUT_FILENAME = 'adobe_examples.json'


def iter_file_paths(path):
  for item in path.iterdir():
    if item.is_dir():
      yield from iter_file_paths(item)
    elif item.is_file():
      yield item


def main(argv):
  payloads = []
  for path in iter_file_paths(CUSTOM_HTTP_DIR):
    if path.suffix != '.json':
      continue

    with open(path, 'r') as in_file:
      data = json.load(in_file)

    match data:
      case {'properties': {'purchase_properties': dict()}}:
        del data['properties']['purchase_properties']

    match data:
      case {'properties': {'custom_properties': dict()}}:
        del data['properties']['custom_properties']

    payloads.append(data)

  with open(HERE / OUTPUT_FILENAME, 'w') as out_file:
    json.dump(payloads, out_file, indent=4)

  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv))
