import boto3
import json
import psycopg2
import time
import uuid

MANIFEST_COLUMN_DEF = [('bucket', 'text'), ('key', 'text'), ('modified', 'integer'), ('tablename', 'text')]

class S3Endpoint:
  DEFAULT_MANIFEST_PREFIX = 'redshift-manifests'

  def __init__(self, bucket, events_prefix, manifest_prefix=DEFAULT_MANIFEST_PREFIX):
    self.bucket = bucket
    self.events_prefix = events_prefix
    self.manifest_prefix = manifest_prefix

class RedshiftEndpoint:
  def __init__(self, host, port, database, user, password, table, column_def):
    self.database = database
    self.user = user
    self.password = password
    self.table = table
    self.column_def = column_def
    self.host = host
    self.port = port

  def connect(self):
    return psycopg2.connect(dbname=self.database, host=self.host, port=self.port, 
      user=self.user, password=self.password)


class S3LoadJob:
  DEFAULT_MANIFEST_TABLE = 'redshift_s3_loader_manifests'
  MANIFEST_COLUMN_DEF = [('bucket', 'text'), ('key', 'text'), ('modified', 'integer'), ('tablename', 'text')]

  def __init__(self, redshift_endpoint, s3_endpoint, role, batch_size=1000, manifest_table=DEFAULT_MANIFEST_TABLE,
    aws_access_key_id=None, aws_secret_access_key=None):
    
    self.redshift_endpoint = redshift_endpoint
    self.s3_endpoint = s3_endpoint
    self.role = role
    self.manifest_table = manifest_table
    self.batch_size = batch_size
    self.aws_access_key_id = aws_access_key_id
    self.aws_secret_access_key = aws_secret_access_key

  def perform(self):
    conn = self.redshift_endpoint.connect()

    if not self.table_exists(conn, self.manifest_table):
      self.create_table(conn, self.manifest_table, MANIFEST_COLUMN_DEF)
      conn.commit()

    if not self.table_exists(conn, self.redshift_endpoint.table):
      self.create_table(conn, self.redshift_endpoint.table, self.redshift_endpoint.column_def)

    previously_copied_files = self.get_previously_copied_files(conn)

    all_files = self.get_all_s3_objects(self.s3_endpoint.bucket, self.s3_endpoint.events_prefix)

    new_files = [f for f in all_files if (f.bucket_name, f.key) not in previously_copied_files]

    if new_files:
      for i in xrange(0, len(new_files), self.batch_size):
        current_batch = new_files[i : i + self.batch_size]
        print "Processing files [{}, {}) out of {} files".format(i, i + self.batch_size, len(new_files))
        manifest_file, manifest_csv_file = self.upload_manifest_files_to_s3(current_batch)

        cur = conn.cursor()
        copy_cmd = self.generate_copy_command(manifest_file)
        print 'Executing COPY command: {}'.format(copy_cmd)
        cur.execute(copy_cmd)
        print 'Finished executing COPY command'

        manifest_copy_cmd = self.generate_copy_manifest_command(manifest_csv_file)
        print 'Executing manifest COPY command: {}'.format(manifest_copy_cmd)
        cur.execute(manifest_copy_cmd)
        print 'Finished executing manifest CSV COPY command'

        conn.commit()
        print 'Success!'
    else:
      print 'There are no more new files in bucket={b} prefix={p} to upload to redshift table={t}'.format(
        b=self.s3_endpoint.bucket, p=self.s3_endpoint.events_prefix, t=self.redshift_endpoint.table)

    conn.close()

  def upload_manifest_files_to_s3(self, s3_objects):
    session = boto3.session.Session(aws_access_key_id=self.aws_access_key_id, aws_secret_access_key=self.aws_secret_access_key) 
    s3 = session.resource('s3')

    # Upload a manifest json for all of the files in <s3_objects>.
    object_uris = map(self.s3_object_to_uri, s3_objects)
    object_uri_entries = map(lambda k: {'url': k, 'mandatory': True}, object_uris)
    manifest_object = {'entries': object_uri_entries}
    manifest_json = json.dumps(manifest_object)

    manifest_filename = '{}/{}.manifest'.format(self.s3_endpoint.manifest_prefix, uuid.uuid1())
    print 'uploading manifest file={} to bucket={}'.format(manifest_filename, self.s3_endpoint.bucket)
    manifest_file = s3.Object(self.s3_endpoint.bucket, manifest_filename)
    manifest_file.put(Body=manifest_json)

    # Also upload a separate csv file corresponding to the rows we are inserting in the manifest table.
    manifest_table_csv_rows = map(
      lambda obj_sum: '{b},{k},{m},{t}'.format(
        b=obj_sum.bucket_name, k=obj_sum.key, m=obj_sum.last_modified.strftime('%s'), t=self.redshift_endpoint.table), 
      s3_objects)
    manifest_csv_contents = '\n'.join(manifest_table_csv_rows)
    
    manifest_csv_filename = '{}.csv'.format(manifest_filename)
    print 'uploading manifest csv file={} to bucket={}'.format(manifest_csv_filename, self.s3_endpoint.bucket)
    manifest_csv_file = s3.Object(self.s3_endpoint.bucket, manifest_csv_filename)
    manifest_csv_file.put(Body=manifest_csv_contents)

    return manifest_file, manifest_csv_file 

  def generate_copy_command(self, manifest_file):
    manifest_file_uri = self.s3_object_to_uri(manifest_file)
    cmd = ("COPY {t} FROM '{m}' "
           "iam_role '{r}' "  
           "format as avro 'auto' "  
           "manifest").format(t=self.redshift_endpoint.table, m=manifest_file_uri, r=self.role)
    return cmd

  def generate_copy_manifest_command(self, manifest_csv):
    manifest_csv_uri = self.s3_object_to_uri(manifest_csv)
    cmd = ("COPY {t} FROM '{f}' "
           "iam_role '{r}' "
           "csv").format(t=self.manifest_table, f=manifest_csv_uri, r=self.role)
    return cmd

  def get_previously_copied_files(self, connection):
    cur = connection.cursor()
    query = "SELECT bucket, key FROM {mt} WHERE tablename='{t}'".format(
      mt=self.manifest_table, t=self.redshift_endpoint.table)
    cur.execute(query)

    return set(cur.fetchall())

  def table_exists(self, connection, table):
    query = "SELECT 1 FROM pg_table_def WHERE tablename = '{}' LIMIT 1".format(table)
    cur = connection.cursor()
    try:
      cur.execute(query)
      result = cur.fetchone()
      return bool(result)
    finally:
      cur.close()

  def create_table(self, connection, table, column_def):
    """
    Expects a list of tuples of (name_str, type_str) for column_def, e.g.
    [('id', 'text'), ('time', 'integer')]
    """
    print 'creating table {} with columns {}'.format(table, column_def)
    query = 'CREATE TABLE {t} ({c})'.format(t=table, c=','.join(
      ['{name} {type}'.format(name=name, type=type_) for name, type_ in column_def]))

    cur = connection.cursor()
    cur.execute(query)

  def get_all_s3_objects(self, bucket, prefix):
    session = boto3.session.Session(aws_access_key_id=self.aws_access_key_id, aws_secret_access_key=self.aws_secret_access_key) 
    s3 = session.resource('s3')
    return s3.Bucket(bucket).objects.filter(Prefix=prefix)

  def s3_object_to_uri(self, s3_object):
    return 's3://{b}/{k}'.format(b=s3_object.bucket_name, k=s3_object.key)


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
  newsfeed_impression_batch_size = 1000

  newsfeed_impression_redshift = RedshiftEndpoint(host, port, database, user, password, 
    newsfeed_impression_redshift_table, newsfeed_impression_redshift_column_def)
  newsfeed_impression_s3 = S3Endpoint(newsfeed_impression_s3_bucket, newsfeed_impression_s3_prefix)

  newsfeed_impression_job = S3LoadJob(newsfeed_impression_redshift, newsfeed_impression_s3, role, batch_size=newsfeed_impression_batch_size, 
    aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
  newsfeed_impression_job.perform()

  '''
  Canvas Entry Avro fields:
  [
    {"name": "id","type": "string"},
    {"name": "user_id","type": "string"},
    {"name": "external_user_id","type": ["null", "string"],"default": null},
    {"name": "time","type": "int"},
    {"name": "canvas_id","type": "string"},
    {"name": "canvas_variation_id","type": "string"},
    {"name": "in_control_group","type": "boolean"}
  ]
  '''
  print 'Loading Canvas Entry...'
  newsfeed_impression_s3_bucket = '<your_currents_bucket>'
  newsfeed_impression_s3_prefix = '<your_prefix_to_event_type=users.canvas.Entry>'
  newsfeed_impression_redshift_table = 'tutorial_canvas_entry'
  canvas_entry_redshift_column_def = [
    ('id', 'text'), 
    ('user_id', 'text'), 
    ('external_user_id', 'text'), 
    ('time', 'integer'), 
    ('canvas_id', 'text'), 
    ('canvas_variation_id', 'text'), 
    ('in_control_group', 'boolean')
  ]

  canvas_entry_redshift = RedshiftEndpoint(host, port, database, user, password, 
    canvas_entry_redshift_table, canvas_entry_redshift_column_def)
  canvas_entry_s3 = S3Endpoint(canvas_entry_s3_bucket, canvas_entry_s3_prefix)

  canvas_entry_job = S3LoadJob(canvas_entry_redshift, canvas_entry_s3, role, 
    aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
  canvas_entry_job.perform()
