#!/usr/bin/env python3

import configparser
import json
import multiprocessing
import time
import sys

from threading import Thread

from boto.s3.connection import S3Connection

from log import log

config = configparser.ConfigParser()
config.read('config')


class Fetcher(multiprocessing.Process):
	"""gets objects from s3"""
	def __init__(self, access_key, secret_key, request_queue):
		multiprocessing.Process.__init__(self)
		self.daemon = True
		self.running = True
		self.access_key = access_key
		self.secret_key = secret_key
		self.request_queue = request_queue

		self.buckets = {}
		self.threads = int(config['tuning']['s3-threads'])

		log.info("Fetcher Started")

	def run(self):	
		workers = [Thread(target=self.jobHandler,) for i in range(self.threads)]
		for i in workers:
			i.daemon = True
			i.start()

	def stop(self):
		self.running = False

	def jobHandler(self):
		conn = S3Connection(self.access_key, self.secret_key)
		while self.running:
			if not self.request_queue.empty():
				m = self.request_queue.get()
				try:
					mp = m.get_body()
					mp = json.loads(mp)
					if mp['Type'] == "Notification":
						success = self.fetchObject(conn, mp)
						if success: m.delete()
				except:
					pass
			else:
				time.sleep(1)
		log.info("Fetcher Stopping")
		sys.exit()

	def fetchObject(self, conn, message):
		m = json.loads(message['Message'])
		bucket, keys = (m['s3Bucket'], m['s3ObjectKey'])

		if not bucket in self.buckets:
			self.buckets[bucket] = conn.get_bucket(bucket)

		for key in keys:
			key = self.buckets[bucket].get_key(key)
			outfile = config['general']['log-path'] + "/" + key.key.replace('/', '-')

			try:
				log.info("Fetching key %s from bucket %s" % (key.key, bucket))
				key.get_contents_to_filename(outfile)
				return True
			except:
				log.warn("Failed to fetch key %s from bucket %s" % (key.key, bucket))
				return False