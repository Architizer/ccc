""" common crawl module """
from gzip import GzipFile
import hashlib
from io import BytesIO, TextIOWrapper
import os
import sys
import json
import time
import logging
import boto3
import requests
from bs4 import BeautifulSoup
from ccc.formatter import Formatter
from ccc.queue_wrapper import QueueWrapper
from redis import Redis

from pywb.cdx.cdxserver import CDXServer
from pywb.utils.wbexception import NotFoundException

LOGGER = logging.getLogger('ccc')
HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
LOGGER.addHandler(HANDLER)
LOGGER.setLevel(logging.INFO)
QUEUE_NAME = os.environ.get('QUEUE_NAME')
QUEUE_ERROR_NAME = os.environ.get('QUEUE_ERROR_NAME')
QUEUE_TYPE = os.environ.get('QUEUE_TYPE')
BACKEND = None
if QUEUE_TYPE == 'redis':
    BACKEND = Redis(host=os.environ.get('REDIS_HOST'), port=os.environ.get('REDIS_PORT'))
elif QUEUE_TYPE == 'sqs':
    BACKEND = boto3.resource('sqs')
QUEUE = QueueWrapper(QUEUE_NAME, QUEUE_TYPE, BACKEND)

def log(msg):
    """ log abstract for debug """
    LOGGER.debug(msg)

def log_info(msg):
    """ log abstract """
    LOGGER.info(msg)

def lookup(index, domain):
    """ looks up index in ccc index """
    config = {'archive_paths': 'https:/s3.amazonaws.com/commoncrawl',
	             'enable_cdx_api': '-index',
	             'enable_memento': True,
	             'framed_replay': False,
	             'max_blocks': 5,
	             'shard_index_loc': {'match': '.*(collections/[^/]+/)',
	                                 'replace': 'https://s3.amazonaws.com/commoncrawl/cc-index/\\1'}}
    try:
        server = CDXServer('collections/{}/indexes/cluster.idx'.format(index), config=config)
        return server.load_cdx(url='{}/*'.format(domain))
    except NotFoundException:
        log('domain not found: {}'.format(domain))
        return list()

def get(page):
    """ extracts page from s3 archive """
    try:
        offset, length = int(page['offset']), int(page['length'])
        offset_end = offset + length - 1
        prefix = 'https://s3.amazonaws.com/commoncrawl/'
        resp = requests.get(prefix + page['filename'],
                            headers={'Range': 'bytes={}-{}'.format(offset, offset_end)})
        raw_data = BytesIO(resp.content)
        io_handle = TextIOWrapper(GzipFile(fileobj=raw_data), encoding='utf-8', errors='ignore')
        return io_handle.read()
    except UnicodeDecodeError:
        log('unicode error: {}'.format(page))
        return None

def _post_to_solr(batch, commit=False):
    """ posts document to solr """
    solr_url = os.environ.get('SOLR_URL', None)
    if not solr_url:
        log("set SOLR_ENV environment variable export SOLR_ENV=localhost:8389")
        sys.exit(1)
    solr_template = '{}/solr/commoncrawl/update?commit={}'
    response = requests.post(solr_template.format(solr_url, str(commit).lower()),
                             headers={"Content-Type":"application/json"},
                             data=json.dumps(batch))
    log_info(response.status_code)
    log_info(response.text)
    return response


def index_in_solr(domain):
    """ indexes document in solr """
    log_info('indexing: {}'.format(domain))
    index = os.environ.get('INDEX', 'CC-MAIN-2016-40')
    batch_size = 20
    batch = []
    counter = 0
    for record in lookup(index, domain):
        log_info('processing record: {}'.format(record))
        formatter = Formatter(domain)
        counter += 1
        record_json = json.loads(''.join(record.split(' ')[2:]))
        data = get(record_json)
        if data:
            document = formatter.get_document(data)
            batch.append(document)
            log_info('indexing: {}'.format(document['url']))
            if len(batch) % batch_size == 0:
                response = _post_to_solr(batch, counter % batch_size*5 == 0)
                log_info('submitting batch of {} documents'.format(len(batch)))
                batch_urls = [doc['url'] for doc in batch]
                if response.status_code == 200:
                    for url in batch_urls:
                        log_info("success for: {}".format(url))
                else:
                    for url in batch_urls:
                        log_info("failed for: {}".format(url))
                    log_info("error message: {}".format(response.text))
                    error_msg = {'status': response.status_code,
                                 'message': response.text,
                                 'domain': domain,
                                 'urls': batch_urls
                                }
                    enqueue_error(json.dumps(error_msg))
                batch = []

    # submitting and committing the rest
    response = _post_to_solr(batch, True)
    log_info('submitting batch of {} documents and committing'.format(len(batch)))
    batch_urls = [doc['url'] for doc in batch]
    if response.status_code == 200:
        for url in batch_urls:
            log_info("success for: {}".format(url))
    else:
        for url in batch_urls:
            log_info("failed for: {}".format(url))
        log_info("error message: {}".format(response.text))
        error_msg = {'status': response.status_code,
                     'message': response.text,
                     'domain': domain,
                     'urls': batch_urls
                    }
        enqueue_error(json.dumps(error_msg))
    batch = []

    log("done")

def enqueue_error(error_msg):
    """ enqueues error to process later """
    error_queue = QueueWrapper(QUEUE_ERROR_NAME, QUEUE_TYPE, BACKEND)
    response = error_queue.send_message(error_msg)
    return response.get('MessageId')

def add_to_pending(domain):
    """ enqueues job """
    log_info('enqueing {}'.format(domain))
    response = QUEUE.send_message(domain)
    return response.get('MessageId')

def dequeued():
    """ dequeues job """
    while True:
        messages = QUEUE.receive_messages(WaitTimeSeconds=5)
        for message in messages:
            domain = message.body
            index_in_solr(domain)
            message.delete()
