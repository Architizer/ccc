import gzip
import requests
from cStringIO import StringIO
from bs4 import BeautifulSoup
import md5
import logging
import sys

from pywb.cdx.cdxserver import CDXServer

def log(msg):
    logger = logging.getLogger('ccc')
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler) 
    logger.setLevel(logging.DEBUG)
    logger.debug(msg)

def lookup(index, domain):
    config = {'archive_paths': 'https:/s3.amazonaws.com/commoncrawl',
	      'enable_cdx_api': '-index',
	      'enable_memento': True,
	      'framed_replay': False,
	      'max_blocks': 5,
	      'shard_index_loc': { 'match': '.*(collections/[^/]+/)',
	                           'replace': 'https://s3.amazonaws.com/commoncrawl/cc-index/\\1'}}
    server = CDXServer('collections/{}/indexes/cluster.idx'.format(index), config=config)
    return server.load_cdx(url='{}/*'.format(domain))

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
