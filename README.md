cloudtrail-poller
=================

### Overview

Cloudtrail-poller captures AWS API logs and writes them to [Ascender](https://github.com/jamiealquiza/ascender)). Via the AWS config, Cloudtrail logs are routinely compressed and dumped to a specified s3 bucket. Additionally, SNS notifications can be sent when new, compressed archives of Cloudtrail logs are available in s3. Cloudtrail-poller works by subscribing and SQS queue to the Cloudtrail SNS notifier and listening to the qeueue for notifications that new log archives available for download. Cloudtrail-poller handles logs in several transactions to ensure reliability of log receipt/delivery, each stage of the transaction handled by different subcomponents:

- `sqsconsumer` binds to an SQS queue and looks for SNS sourced notifications. Each notification includes a pointer to an s3 object representing a set of Cloudtrail logs. The SQS consumer component pops messages from the queue and temporarily sets message invisibility, passing the s3 information to `s3fetcher`.
- `s3fetcher` receives the SQS message object and the s3 object reference for download. Only upon successful download of the s3 object will `s3fetcher` send a delete request for the respective SQS message that pointed to the object. This ensures that each notification of Cloudtrail log availability results in a safe, locally stored copy. 
- `inflator` monitors the local s3 output directory for available Cloudtrail log archives. It decompresses and breaks out batches of logs into individual messages and ships them off to their remote destination (Ascender). Log archives are only removed when a count of 200 responses from Ascender is equal to the number of logs found in the archive.

### Setup

Cloudtrail-poller is built on Python 3 and the only external dependency is Boto. The configuration file should be named `config` and filled out accordingly based on the `config.example` file.

<pre>
[general]
# Path for s3 object storage. Must be created beforehand and accessible by cloudtrail-poller.
log-path: out

[ascender]
ip: 127.0.0.1
port: 6030

[aws-sqs]
# Access to read and delete messages from the SNS subscribed SQS queue.
name: queue
region: us-west-2
access: xxx 
secret: xxxxxx

[aws-s3]
# Access to download s3 objects from the Cloudtrail bucket.
access: xxx 
secret: xxxxxx

[tuning]
# sqsconsumer and s3fetcher run as separate processes (workers) with thread pools (threads).
# Likely doesn't need adjustments, but could benefit from increased thread counts for imporoved performance.
sqs-workers: 1
sqs-threads: 3
s3-workers: 1
s3-threads: 8
</pre>

Start cloudtrail-poller by running `app.py`:
<pre>
 % ./app.py
2015-03-10 08:24:02,037 | INFO | Consumer Started: connected to sqs-cloudtrail with 3 threads
2015-03-10 08:24:02,040 | INFO | Fetcher Started
2015-03-10 08:24:02,056 | INFO | Inflator Started
2015-03-10 08:24:04,949 | INFO | Fetching key cloudtrail/AWSLogs/185869774838/CloudTrail/us-west-2/2015/03/10/185869774838_CloudTrail_us-west-2_20150310T0020Z_UvH8rrsNWQSZwTpt.json.gz from bucket s3-some-bucket
2015-03-10 08:24:04,959 | INFO | Fetching key cloudtrail/AWSLogs/185869774838/CloudTrail/us-west-2/2015/03/10/185869774838_CloudTrail_us-west-2_20150310T0005Z_XD54DnXlC0LuSnfw.json.gz from bucket s3-some-bucket
2015-03-10 08:24:04,969 | INFO | Fetching key cloudtrail/AWSLogs/185869774838/CloudTrail/us-west-2/2015/03/09/185869774838_CloudTrail_us-west-2_20150309T2220Z_3uWP8zY1gXwPyKcL.json.gz from bucket s3-some-bucket
2015-03-10 08:24:04,981 | INFO | Fetching key cloudtrail/AWSLogs/185869774838/CloudTrail/us-west-2/2015/03/10/185869774838_CloudTrail_us-west-2_20150310T0120Z_qI4YAcxETjyDGHP4.json.gz from bucket s3-some-bucket
</pre>
