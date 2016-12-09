import unittest
import json
from ccc.formatter import Formatter
from ccc import lookup

class TestFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = Formatter('architizer.com')

    def read_good_record_fixture(self):
        return """
            WARC-Target-URI: http://architizer.com/about
            WARC-Test: test warc value
            WARC-Record-ID: record-id
            \n\n
            HTTP/1.1 200 OK
            Content-Type: text/html
            Header-Test: test header value
            \n\n
            <html>
            <head>
            <title>expected title</title>
            <meta property="og:tag" content="value" />
            <meta name="description" content="this site is amazing" />
            </head>
            hello bello
            </html>
        """

    def read_bad_record_fixture(self):
        return """
            WARC-Target-URI: http://architizer.com/about
            WARC-Record-ID: record-id
            \n\n
            Content-Type: text/html
            \n\n
            <html>
            <head>
            </head>
            </html>
        """

    def test_has_domain_field(self):
        expected = 'example.com' 
        document = Formatter(expected).get_document(self.read_good_record_fixture())
        assert document['domain'] == expected

    def test_has_uri(self):
        expected = 'http://architizer.com/about'
        document = self.formatter.get_document(self.read_good_record_fixture())
        assert document['url'] == expected

    def test_has_title(self):
        expected = "expected title"
        document = self.formatter.get_document(self.read_good_record_fixture())
        assert document['title'] == expected

    def test_has_title_empty(self):
        document = self.formatter.get_document(self.read_bad_record_fixture())
        assert not document.get('title')

    def test_has_content_type(self):
        expected = "text/html"
        document = self.formatter.get_document(self.read_bad_record_fixture())
        assert document.get('Content-Type') == expected

    def test_has_description(self):
        expected = "this site is amazing"
        document = self.formatter.get_document(self.read_good_record_fixture())
        assert document.get('meta:description') == expected

    def test_has_meta(self):
        expected = "value"
        document = self.formatter.get_document(self.read_good_record_fixture())
        assert document.get('meta:og:tag') == expected

    def test_has_text(self):
        expected = "hello bello" 
        document = self.formatter.get_document(self.read_good_record_fixture())
        assert expected in document.get('text')

    def test_has_no_text(self):
        document = self.formatter.get_document(self.read_bad_record_fixture())
        assert len(document.get('text')) == 0

    def test_id(self):
        document = self.formatter.get_document(self.read_bad_record_fixture())
        assert len(document.get('id')) > 0

    def test_warc_header(self):
        document = self.formatter.get_document(self.read_good_record_fixture())
        assert document.get('WARC-Test') == 'test warc value'

    def test_header(self):
        document = self.formatter.get_document(self.read_good_record_fixture())
        assert document.get('Header-Test') == 'test header value'

    def test_warc_id(self):
        document = self.formatter.get_document(self.read_good_record_fixture())
        assert document.get('WARC-Record-ID') == 'record-id'

if __name__ == '__main__':
    unittest.main()
