import gzip
import requests
from cStringIO import StringIO
from bs4 import BeautifulSoup
import md5
import logging
import os
import sys
import json
import redis
import time

from pywb.cdx.cdxserver import CDXServer
from pywb.utils.wbexception import NotFoundException

logger = logging.getLogger('ccc')
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler) 
logger.setLevel(logging.INFO)

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

    raw_data = StringIO(resp.content)
    f = gzip.GzipFile(fileobj=raw_data)
    return f.read()

def format(record):
    warc, header, response = record.strip().split('\r\n\r\n', 2)
    soup = BeautifulSoup(response, "html.parser")

    for script in soup(["script", "style"]):
        script.extract()
    warc_dict = {}
    for warc_element in  warc.split("\r\n"):
        elements = warc_element.split(":")
        head, tail = elements[0], elements[1:]
        warc_dict[head] = ':'.join(tail)
    header_dict = {}
    for header_element in  header.split("\r\n"):
        elements = header_element.split(":")
        head, tail = elements[0], elements[1:]
        header_dict[head] = ':'.join(tail)

    document = {}
    if soup.title:
        document['title'] = soup.title.text
    if soup.head:
        for meta in soup.head.find_all('meta'):
            prop = meta.get('property')
            if not prop:
                prop = meta.get('name')
            content = meta.get('content')

            document["meta:"+str(prop)] = content
    document.update(warc_dict)
    document.update(header_dict)
    document['description'] = document.get('meta:description', '')
    document['text'] = ' '.join(soup.get_text().split())
    document['url'] = warc_dict['WARC-Target-URI']
    document['id'] = md5.new(document['text'].encode('ascii','ignore')).hexdigest()
    return document

def index_in_solr(domain):
    index = os.environ.get('INDEX', 'CC-MAIN-2016-40')
    solr_url = os.environ.get('SOLR_URL', None)
    if not solr_url:
        log("set SOLR_ENV environment variable export SOLR_ENV=localhost:8389")
        sys.exit(1)
    for record in lookup(index, domain):
        record_json = json.loads(''.join(record.split(' ')[2:]))
        data = get(record_json)
        document = format(data)
        log(document)
        solr_doc = {'add': { 'doc': document }}
        response =requests.post('{}/solr/test/update?wt=json'.format(solr_url),
                                headers={"Content-Type":"application/json"},
                                data=json.dumps(solr_doc))
        log(response)
        log_info('indexing: {}'.format(document['url']))
    
    response =requests.post('{}/solr/test/update?wt=json'.format(solr_url),
                            headers={"Content-Type":"application/json"},
                            data=json.dumps({'add': { 'doc': {} }, 'commit': {} }))
    log(response)
    log("done")

def add_to_pending(domain):
    r = redis.StrictRedis(host='redis', port=6379, db=0)
    return r.rpush('domains', domain)

def dequeued():
    r = redis.StrictRedis(host='redis', port=6379, db=0)
    while True:
        time.sleep(5)
        domain = r.lpop('domains')
        log_info('dequeing {}'.format(domain))
        if domain:
            index_in_solr(domain)