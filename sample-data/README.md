# Sample Data

This directory contains sample data produced by the Braze Currents storage Integrations. See the full documentation for more details about Braze Currents: [https://www.braze.com/docs/partners/braze_currents/how_it_works/](https://www.braze.com/docs/partners/braze_currents/how_it_works/)

## Contents
This directory contains sample Avro files and JSON files for the different event types uploaded by the integration. There is a file for each event type streamed through Currents.

The Avro files can be read or the schema extracted with avro-tools:
```
$ avro-tools tojson Avro/{EVENT}.avro
$ avro-tools getschema Avro/{EVENT}.avro
```

Note: The JSON file is just a decoded version of the Avro file, provided only for readability. We do not stream JSON in Braze Currents.
