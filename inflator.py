#!/usr/bin/env python3

import configparser
import gzip
import json
import multiprocessing
import os
import time
import sys

from threading import Thread

import ascender
from log import log

config = configparser.ConfigParser()
config.read('config')

try:
	a = ascender.Client(config['ascender']['ip'], int(config['ascender']['port']))
except Exception as e:
	log.info("Error connecting to Ascender: %s" % e)
	sys.exit(1)


class Inflator(multiprocessing.Process):
	"""decompresses cloudtrail s3 logs"""
	def __init__(self):
		multiprocessing.Process.__init__(self)
		self.daemon = True
		self.running = True
		self.exit = multiprocessing.Event()
		self.logdir = config['general']['log-path']

		log.info("Inflator Started")

	def run(self):
		while self.running:
			self.files = os.listdir(self.logdir)
			if len(self.files) > 0:
				for i in self.files:
					self.inflate(i)
			else:
				try:
					time.sleep(5)
				except:
					break
		log.info("Inflator Stopping")
		sys.exit()

	def stop(self):
		self.running = False

	def inflate(self, zipf):
		self.out = {}
		fpath = self.logdir + "/" + zipf
		try:
			with gzip.open(fpath) as f:
				if f._read():
					self.out = json.loads(f.read().decode('utf-8'))['Records']
		except:
			log.warn("Failed to uncompress %s" % zipf)
			return

		count = len(self.out)
		acked = 0
		for i in self.out: 
			i['@type'] = "aws-cloudtrail"
			try:
				resp = a.send(json.dumps(i))
			except Exception as e:
				log.info("Error sending to Ascender: %s" % e)
				time.sleep(5)
				break
			log.info("Ascender response: %s" % resp)
			rcode = resp.split('|')[0] 
			if rcode == "200":
				acked += 1
				if acked == count: 
					try:
						os.remove(fpath)
					except Exception as e:
						log.warn(e)
			elif rcode == "503":
				time.sleep(1)
