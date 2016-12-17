"""
A module that generates the document that
is to be inserted into search collection.
"""

import hashlib
from bs4 import BeautifulSoup


class Formatter(object):
    """
    Module has to goals parse html and produce document
    """
    def __init__(self, domain):
        """
        initializes instance with a domain
        """
        self.domain = domain
        self.document = {}
        self.document['domain'] = domain

    def parse_html(self, response):
        """
        This uses beautifulsoup to parse the html page
        """
        soup = BeautifulSoup(response, "html.parser")
        if soup.title:
            self.document['title'] = soup.title.text
        for script in soup(["script", "style"]):
            script.extract()
        if soup.head:
            for meta in soup.head.find_all('meta'):
                prop = meta.get('property')
                if not prop:
                    prop = meta.get('name')
                content = meta.get('content')

                self.document["meta:"+str(prop)] = content
        self.document['text'] = ' '.join(soup.get_text().split())

    def get_document(self, record):
        """
        This returns the processed document for the search collection
        """
        warc, header, response = record.strip().split('\n\n', 2)
        self.parse_html(response)
        warc_dict = {}
        for warc_element in warc.split("\n"):
            elements = warc_element.split(":")
            head, tail = elements[0], elements[1:]
            warc_dict[head.strip()] = ':'.join(tail).strip()
        header_dict = {}
        for header_element in header.split("\n"):
            elements = header_element.split(":")
            head, tail = elements[0], elements[1:]
            header_dict[head.strip()] = ':'.join(tail).strip()
        self.document.update(warc_dict)
        self.document.update(header_dict)
        self.document['url'] = warc_dict['WARC-Target-URI']
        md5 = hashlib.md5()
        md5.update(self.document['text'].encode('ascii', 'ignore'))
        self.document['id'] = warc_dict['WARC-Payload-Digest']
        return self.document
