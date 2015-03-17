#!/usr/bin/env python3

import configparser
import json
import multiprocessing
import time
import sys

from threading import Thread

import boto.sqs

from log import log

config = configparser.ConfigParser()
config.read('config')

statsQueue = multiprocessing.Queue()


class Consumer(multiprocessing.Process):
	"""reads sqs"""
	def __init__(self, sqs_queue, region, access_key, secret_key, output_queue, queue_cap):
		multiprocessing.Process.__init__(self)
		self.daemon = True
		self.running = True
		self.sqs_queue = sqs_queue
		self.region = region
		self.access_key = access_key
		self.secret_key = secret_key
		self.output_queue = output_queue
		self.queue_cap = queue_cap

		self.threads = int(config['tuning']['sqs-threads'])
		log.info("Consumer Started: connected to %s with %s threads" % (sqs_queue, self.threads))

	def run(self):
		n = int(config['tuning']['sqs-threads'])
		workers = [Thread(target=self.poll,) for i in range(self.threads)]
		for i in workers:
			i.daemon = True
			i.start()

	def stop(self):
		self.running = False

	def poll(self):
		conn = boto.sqs.connect_to_region(self.region,
			aws_access_key_id=self.access_key,
			aws_secret_access_key=self.secret_key)
		sqs = conn.get_queue(self.sqs_queue)
		sqs.set_message_class(boto.sqs.message.RawMessage)

		while self.running:
			self.fetchMessages(sqs)
			'''# This doesn't work on Mac OS.
			if self.output_queue.qsize() < self.queue_cap:
				self.fetchMessages()
			else:
				time.sleep(3)'''
		log.info("Consumer Stopping")
		sys.exit()

	def fetchMessages(self, sqs):
		r = sqs.get_messages(num_messages=10)
		if len(r) > 0:
			self.parseMessage(r)
		else:
			time.sleep(5)

	def parseMessage(self, batch):
		statsQueue.put(len(batch))
		for i in batch:
			self.output_queue.put(i)


class Statser(Thread):
    """outputs periodic stats info"""
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.running = True

    def run(self):
        count_current = count_previous = 0

        while self.running:
            # Handle rate stats.
            stop = time.time()+5
            while time.time() < stop:
                if not statsQueue.empty():
                    count_current += statsQueue.get()
                else:
                    time.sleep(0.25)
            if count_current > count_previous:
                # We divide by the actual duration because thread scheduling /
                # wall time vs. execution time can't be trusted.
                duration = time.time() - stop + 5
                rate = count_current / duration
                log.info("Last %.1fs: polled %.2f messages/sec." % (duration, rate))
            count_previous = count_current = 0

    def stop(self):
    	self.running = False