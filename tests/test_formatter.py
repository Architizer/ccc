""" Formatter test """
import unittest
from ccc.formatter import Formatter

class TestFormatter(unittest.TestCase):
    """ Tests formatter """
    def setUp(self):
        """ setup records and initialize formatter """
        self.formatter = Formatter('architizer.com')
        self.good_record = """
            WARC-Target-URI: http://architizer.com/about
            WARC-Test: test warc value
            WARC-Record-ID: record-id
            WARC-Payload-Digest: fingerprint
            Content-Type: application/http; msgtype=response
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
        self.bad_record = """
            WARC-Target-URI: http://architizer.com/about
            WARC-Record-ID: record-id
            WARC-Payload-Digest: fingerprint
            \n\n
            Content-Type: text/html
            \n\n
            <html>
            <head>
            </head>
            </html>
        """

    def test_has_domain_field(self):
        """ document should have domain field """
        expected = 'example.com'
        document = Formatter(expected).get_document(self.good_record)
        assert document['domain'] == expected

    def test_has_uri(self):
        """ document should have uri """
        expected = 'http://architizer.com/about'
        document = self.formatter.get_document(self.good_record)
        assert document['url'] == expected

    def test_has_title(self):
        """ document should have title """
        expected = "expected title"
        document = self.formatter.get_document(self.good_record)
        assert document['title'] == expected

    def test_has_title_empty(self):
        """ document should handle it if there is no title """
        document = self.formatter.get_document(self.bad_record)
        assert not document.get('title')

    def test_has_content_type(self):
        """ document should have content type """
        expected = "text/html"
        document = self.formatter.get_document(self.bad_record)
        assert document.get('Content-Type') == expected

    def test_has_description(self):
        """ document should have description """
        expected = "this site is amazing"
        document = self.formatter.get_document(self.good_record)
        assert document.get('meta:description') == expected

    def test_has_meta(self):
        """ document should have all the meta data """
        expected = "value"
        document = self.formatter.get_document(self.good_record)
        assert document.get('meta:og:tag') == expected

    def test_has_text(self):
        """ document should contain the text """
        expected = "hello bello"
        document = self.formatter.get_document(self.good_record)
        assert expected in document.get('text')

    def test_has_no_text(self):
        """ document should handle it if there is no text """
        document = self.formatter.get_document(self.bad_record)
        assert len(document.get('text')) == 0

    def test_id(self):
        """ document should produce and id """
        document = self.formatter.get_document(self.bad_record)
        assert len(document.get('id')) > 0

    def test_warc_header(self):
        """ document should have warc header """
        document = self.formatter.get_document(self.good_record)
        assert document.get('WARC-Test') == 'test warc value'

    def test_header(self):
        """ document should have header """
        document = self.formatter.get_document(self.good_record)
        assert document.get('Header-Test') == 'test header value'

    def test_take_html_content_type_header(self):
        document = self.formatter.get_document(self.good_record)
        expected = 'text/html'
        assert document.get('Content-Type') == expected

    def test_warc_id(self):
        """ document should have warc id """
        document = self.formatter.get_document(self.good_record)
        assert document.get('WARC-Record-ID') == 'record-id'

if __name__ == '__main__':
    unittest.main()
