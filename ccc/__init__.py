import boto3
from gzip import GzipFile
import requests
from io import BytesIO
from bs4 import BeautifulSoup
import hashlib
import logging
import os
import sys
import json
import redis
import time
from ccc.formatter import Formatter

from io import TextIOWrapper
from pywb.cdx.cdxserver import CDXServer
from pywb.utils.wbexception import NotFoundException

logger = logging.getLogger('ccc')
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler) 
logger.setLevel(logging.INFO)
redis_client = redis.StrictRedis(host=os.environ.get('REDIS_HOST', '127.0.0.1'),
                                 port=6379, db=0)

def log(msg):
    logger.debug(msg)

def log_info(msg):
    logger.info(msg)

def lookup(index, domain):
    config = {'archive_paths': 'https:/s3.amazonaws.com/commoncrawl',
	      'enable_cdx_api': '-index',
	      'enable_memento': True,
	      'framed_replay': False,
	      'max_blocks': 5,
	      'shard_index_loc': { 'match': '.*(collections/[^/]+/)',
	                           'replace': 'https://s3.amazonaws.com/commoncrawl/cc-index/\\1'}}
    response = list()
    try:
        server = CDXServer('collections/{}/indexes/cluster.idx'.format(index), config=config)
        response = server.load_cdx(url='{}/*'.format(domain))
    except NotFoundException:
        log('domain not found'.format(domain))
    return response

def get(page):
    offset, length = int(page['offset']), int(page['length'])
    offset_end = offset + length - 1
    prefix = 'https://s3.amazonaws.com/commoncrawl/'
    resp = requests.get(prefix + page['filename'], headers={'Range': 'bytes={}-{}'.format(offset, offset_end)})
    raw_data = BytesIO(resp.content)
    f = TextIOWrapper(GzipFile(fileobj=raw_data), encoding='utf-8', errors='ignore')
    return f.read()

def _post_to_solr(batch, commit=False):
    solr_url = os.environ.get('SOLR_URL', None)
    if not solr_url:
        log("set SOLR_ENV environment variable export SOLR_ENV=localhost:8389")
        sys.exit(1)
    response = requests.post('{}/solr/commoncrawl/update?commit={}'.format(solr_url, str(commit).lower()),
                             headers={"Content-Type":"application/json"},
                             data=json.dumps(batch))
    log_info(response)
    return response.status_code


def index_in_solr(domain):
    index = os.environ.get('INDEX', 'CC-MAIN-2016-40')
    batch_size = 20
    batch = []
    counter = 0
    formatter = Formatter(domain)
    for record in lookup(index, domain):
        counter += 1
        record_json = json.loads(''.join(record.split(' ')[2:]))
        data = get(record_json)
        if data:
            document = formatter.get_document(data)
            batch.append(document)
            log_info('indexing: {}'.format(document['url']))
            if len(batch) % batch_size == 0:
                status_code = _post_to_solr(batch, counter % batch_size*5 == 0)
                log_info('submitting batch of {} documents'.format(len(batch)))
                if status_code == 200:
                    batch = []
    # submitting and committing the rest
    status_code = _post_to_solr(batch, True)
    log_info('submitting batch of {} documents and committing'.format(len(batch)))
    if status_code == 200:
        batch = []
    log("done")

def add_to_pending(domain):
    sqs = boto3.resource('sqs')
    log_info('enqueing {}'.format(domain))
    queue = sqs.get_queue_by_name(QueueName='search-us-east-1-dev')
    response = queue.send_message(MessageBody=domain)
    return response.get('MessageId')

def dequeued():
    sqs = boto3.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName='search-us-east-1-dev')
    while True:
        messages = queue.receive_messages(WaitTimeSeconds=5)
        for message in messages:
            domain = message.body
            index_in_solr(domain)
            message.delete()
