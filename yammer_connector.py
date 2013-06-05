# coding: utf-8

from config import *
from urlparse import urlparse, parse_qs
import BaseHTTPServer
import json
import logging
import os
import urllib

__all__ = ["YammerConnector"]

class YammerConnector(object):
    """
    Objects of this class holds a connection to an Yammer account.
    """

    def connect(self):
        """
        Connect to Yammer account, return True if successful, False otherwise
        """
        # Check if there is a saved access_token
        if os.path.exists(os.path.expanduser(ACCESS_TOKEN_FILE)):
            with open(os.path.expanduser(ACCESS_TOKEN_FILE)) as f:
                self.access_token = f.read()
        else:
            self._request_access_token_and_save()

        return True

    def _request_access_token_and_save(self):
        """
        The Access token is saved in a file to avoid asking all the time.  When
        this method is called, some instructions are presented to the user to
        get the access code, then, saves it into a file
        """
        # Request access token and save to file
        class Handler(BaseHTTPServer.BaseHTTPRequestHandler):

            def do_GET(self_):
                result = urlparse(self_.path)
                self.access_code = parse_qs(result.query)['code'][0]
                self_.wfile.write("<p>Thank you. You may now close this page.</p>")

        server = BaseHTTPServer.HTTPServer(("", 8080), Handler)

        print "Now, please open https://www.yammer.com/dialog/oauth?client_id=%s&redirect_uri=http://localhost:8080" % YAMMER_CONSUMER_KEY
        server.handle_request()

        u = urllib.urlopen('https://www.yammer.com/oauth2/access_token.json?client_id=%s&client_secret=%s&code=%s' % (YAMMER_CONSUMER_KEY, YAMMER_CONSUMER_SECRET, self.access_code))
        data = json.load(u)
        self.access_token = data['access_token']['token']

        # Save to file
        with open(os.path.expanduser(ACCESS_TOKEN_FILE), 'w') as f:
            f.write(self.access_token)

    def get_users(self):
        """
        This method returns a generator that yields parsed JSON user objects.
        It paginates until there's no data left.
        """
        page = 1

        while True:
            try:
                u = urllib.urlopen('https://www.yammer.com/api/v1/users.json?&access_token=%s&page=%d' % (self.access_token, page))
            except IOError as e:
                if e.args[0] == 'http error' and e.args[1] == 401:
                    self._request_access_token_and_save()
                    continue
                else:
                    raise e

            if u.getcode() == 200:
                users = json.load(u)
                if not users:
                    break
                page += 1
            elif u.getcode() == 400:
                self._request_access_token_and_save()
                continue
            else:
                logging.fatal("Could not get users from Yammer. Response code: %d" % u.getcode())
                break

            for user in users:
                yield user

