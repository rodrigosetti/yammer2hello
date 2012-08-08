# coding: utf-8

from config import *
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
                self.accessToken = f.read()
        else:
            self._requestAccessTokenAndSave()

        return True

    def _requestAccessTokenAndSave(self):
        """
        The Access token is saved in a file to avoid asking all the time.  When
        this method is called, some instructions are presented to the user to
        get the access code, then, saves it into a file
        """
        # Request access token and save to file
        print "Instructions to authorize Yammer:"
        print "1. Please goto https://www.yammer.com/dialog/oauth?client_id=%s" % YAMMER_CONSUMER_KEY
        print "2. Log-in, if not already, then authorize the Application"
        self.accessToken = raw_input("3. You will be redirected, please copy from the URL, the text after access_token= and paste here: ")

        # Save to file
        with open(os.path.expanduser(ACCESS_TOKEN_FILE), 'w') as f:
            f.write(self.accessToken)

    def getUsers(self):
        """
        This method returns a generator that yields parsed JSON user objects.
        It paginates until there's no data left.
        """
        page = 1

        while True:
            u = urllib.urlopen('https://www.yammer.com/api/v1/users.json?&access_token=%s&page=%d' % (self.accessToken, page))
            if u.getcode() == 200:
                users = json.load(u)
                if not users:
                    break
                page += 1
            elif u.getcode() == 400:
                self._requestAccessTokenAndSave()
                continue
            else:
                logging.fatal("Could not get users from Yammer. Response code: %d" % u.getcode())
                break

            for user in users:
                yield user

