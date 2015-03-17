#!/usr/bin/env python3

import configparser
import multiprocessing
import time

import inflator
import s3fetcher
import sqsconsumer
from log import log

config = configparser.ConfigParser()
config.read('config')

transferQueue = multiprocessing.Queue()

if __name__ == "__main__":
	consumerStats = sqsconsumer.Statser()
	consumerStats.start()


	for i in range(int(config['tuning']['sqs-workers'])):
		consumer = sqsconsumer.Consumer(sqs_queue=config['aws-sqs']['name'],
			region=config['aws-sqs']['region'],
			access_key=config['aws-sqs']['access'],
			secret_key=config['aws-sqs']['secret'],
			output_queue=transferQueue,
			queue_cap=8)
		consumer.run()


	for i in range(int(config['tuning']['s3-workers'])):
		fetcher = s3fetcher.Fetcher(access_key=config['aws-s3']['access'],
			secret_key=config['aws-s3']['secret'],
			request_queue=transferQueue)
		fetcher.run()


	inflator = inflator.Inflator()
	inflator.run()

	try:
		while True:
			time.sleep(3)
	except KeyboardInterrupt:
		consumerStats.stop()
		consumer.stop()
		fetcher.stop()
		inflator.stop()