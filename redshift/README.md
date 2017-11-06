# Sample Currents S3 to Redshift Loader
## Overview

The basic premise of the code within `s3loader.py` involves using a separate manifest table in the same Redshift database to keep track 
of the files that have already been copied. The general structure is as follows:
1. List all of the files in S3, identify the new files since the last time you've ran `s3loader.py` by comparing the list with
the contents in the manifest table.
2. Create a [manifest](http://docs.aws.amazon.com/redshift/latest/dg/loading-data-files-using-manifest.html) 
file containing the new files.
3. Execute a COPY query to copy the new files from S3 to Redshift using the manifest file.
4. Insert the names of the files that are copied into the separate manifest table in Redshift.
5. Commit.

## Dependencies

You must install the AWS Python SDK and Psycopg in order to run the Loader:

```
pip install boto3
pip install psycopg2
```

## Permissions
### Redshift Role with S3 Read Access
If you have not done so, follow the AWS Documentation to create a Role that is able to execute COPY commands on your files in S3:
http://docs.aws.amazon.com/redshift/latest/gsg/rs-gsg-create-an-iam-role.html.

### Redshift VPC Inbound Rules
If your Redshift cluster is in a VPC, you must configure the VPC to allow connections from the server that you are running the S3 Loader. 
Go into your Redshift Cluster and select the VPC Security Groups entry that you want the Loader to connect into. Next, add a new Inbound Rule:
Type = Redshift, Protocol = TCP, Port = the port for your cluster, Source = Anywhere (or wherever the Loader is running)/

### IAM User with S3 Full Access
The S3 Loader requires read access to the files containing your Currents data, and full access to the location for the manifest files that it generates
for the Redshift COPY commands. The easiest thing to do to accomplish this is to create a new IAM User with the `AmazonS3FullAccess` permissions:
https://console.aws.amazon.com/iam/home#/users. Be sure to save the credentials as you will need to pass them to the Loader.

You can pass the access credentials to the Loader via environment variables, the shared credential file (~/.aws/credentials), or the AWS Config File (http://boto3.readthedocs.io/en/latest/guide/configuration.html#configuring-credentials). Alternatively you may include them directly in the Loader 
by assigning them to the `aws_access_key_id` and the `aws_secret_access_key` fields within an `S3LoadJob` object, but we do not recommend that 
you hard code the credentials within your source code.

## Usage
### Sample Usage
Below is a sample program that loads data for the `users.behaviors.app.NewsFeedImpression` event from S3 to the 
`tutorial_newsfeed_impression` table in Redshift. 

```
if __name__ == '__main__':
  host = '<your_host>.redshift.amazonaws.com'
  port = 5439
  database = '<your_db>'
  user = '<your_db_user>'
  password = '<your_db_password>'
  role = '<your_redshift_role_with_s3_read_access>'

  # Do not hard code these credentials.
  aws_access_key_id = None
  aws_secret_access_key = None

  '''
  News Feed Impression Avro fields:
  [
    {"name": "id", "type": "string"}, 
    {"name": "user_id", "type": "string"},
    {"name": "external_user_id", "type": ["null", "string"], "default": null},
    {"name": "app_id", "type": "string"}, 
    {"name": "time", "type": "int"},
    {"name": "platform", "type": ["null", "string"], "default": null},
    {"name": "os_version", "type": ["null", "string"], "default": null},
    {"name": "device_model", "type": ["null", "string"], "default": null}
  ]  
  '''
  print 'Loading News Feed Impression...'
  newsfeed_impression_s3_bucket = '<your_currents_bucket>'
  newsfeed_impression_s3_prefix = '<your_prefix_to_event_type=users.behaviors.app.NewsFeedImpression>'
  newsfeed_impression_redshift_table = 'tutorial_newsfeed_impression'
  newsfeed_impression_redshift_column_def = [
    ('id', 'text'),
    ('user_id', 'text'),
    ('external_user_id', 'text'), 
    ('app_id', 'text'),
    ('time', 'integer'),
    ('platform', 'text'),
    ('os_version', 'text'),
    ('device_model', 'text')
  ]

  newsfeed_impression_redshift = RedshiftEndpoint(host, port, database, user, password, 
    newsfeed_impression_redshift_table, newsfeed_impression_redshift_column_def)
  newsfeed_impression_s3 = S3Endpoint(newsfeed_impression_s3_bucket, newsfeed_impression_s3_prefix)

  newsfeed_impression_job = S3LoadJob(newsfeed_impression_redshift, newsfeed_impression_s3, role, 
    aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
  newsfeed_impression_job.perform()
```

### Credentials
In order to run the Loader, you must first provide the `host`, `port`, and `database` of your Redshift cluster as well as 
the `user` and `password` of a Redshift user that can run `COPY` queries. Additionally, you must provide the ARN of the 
Redshift Role with S3 Read Access that you've created from a previous section.

```
  host = '<your_host>.redshift.amazonaws.com'
  port = 5439
  database = '<your_db>'
  user = '<your_db_user>'
  password = '<your_db_password>'
  role = '<your_redshift_role_with_s3_read_access>'
```

### Job Configuration
You must provide the S3 Bucket and Prefix of your event files, as well as the Redshift table name that you want to COPY into.

In addition, in order to COPY Avro files with the "auto" option as required by the Loader, the column definition in your Redshift 
table must match the field names in the Avro schema as shown in the Sample program, with the appropriate type mapping 
(e.g. "string" to "text", "int" to "integer"). 

You may also pass in a `batch_size` option to the Loader if you deem that it takes too long to copy all of the files at once. Passing a
`batch_size` allows the Loader to incrementally copy and commit one batch at a time without having to copy everything at the same time.
The time that it takes to load one batch depends on the `batch_size` as well as the size of your files and the size of your Redshift
cluster.

``` 
  '''
  News Feed Impression Avro fields:
  [
    {"name": "id", "type": "string"}, 
    {"name": "user_id", "type": "string"},
    {"name": "external_user_id", "type": ["null", "string"], "default": null},
    {"name": "app_id", "type": "string"}, 
    {"name": "time", "type": "int"},
    {"name": "platform", "type": ["null", "string"], "default": null},
    {"name": "os_version", "type": ["null", "string"], "default": null},
    {"name": "device_model", "type": ["null", "string"], "default": null}
  ]  
  '''
  newsfeed_impression_s3_bucket = '<your_currents_bucket>'
  newsfeed_impression_s3_prefix = '<your_prefix_to_event_type=users.behaviors.app.NewsFeedImpression>'
  newsfeed_impression_redshift_table = 'tutorial_newsfeed_impression'
  newsfeed_impression_redshift_column_def = [
    ('id', 'text'),
    ('user_id', 'text'),
    ('external_user_id', 'text'), 
    ('app_id', 'text'),
    ('time', 'integer'),
    ('platform', 'text'),
    ('os_version', 'text'),
    ('device_model', 'text')
  ]
  newsfeed_impression_batch_size = 1000
```

