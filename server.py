import falcon
import json
import ccc

class CommoncrawlResource:
    def on_post(self, req, resp, domain):
        ccc.add_to_pending(domain)
        resp.body = json.dumps({})
 
api = falcon.API()
api.add_route('/domain/{domain}', CommoncrawlResource())
