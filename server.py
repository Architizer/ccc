""" light weight api to accept domains """
import json
import falcon
import ccc

class CommoncrawlResource:
    """ API resource """
    def on_post(self, req, resp, domain):
        """ accepts posts requests """
        ccc.add_to_pending(domain)
        resp.body = json.dumps({})

class HealthCheck():
    """ API endpoint for loadbalancer registration """
    def on_get(self, req, resp):
        """ accepts get reqeusts """
        resp.body = json.dumps({})

API = falcon.API()
API.add_route('/domain/{domain}', CommoncrawlResource())
API.add_route('/hc', HealthCheck())
