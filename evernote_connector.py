# coding: utf-8

from config import *
import logging
import re

from evernote.edam.error.ttypes import EDAMUserException, EDAMSystemException
from evernote.edam.notestore import NoteStore
from evernote.edam.userstore import UserStore
import thrift.protocol.TBinaryProtocol as TBinaryProtocol
import thrift.transport.THttpClient as THttpClient

__all__ = ['EvernoteConnector']

AUTHENTICATED_API_CALLS = ['copyNote', 'createLinkedNotebook', 'createNote',
                           'createNotebook', 'createSearch',
                           'createSharedNotebook', 'createTag', 'deleteNote',
                           'emailNote', 'expungeInactiveNotes',
                           'expungeLinkedNotebook', 'expungeNote',
                           'expungeNotebook', 'expungeNotes', 'expungeSearch',
                           'expungeSharedNotebooks', 'expungeTag',
                           'findNoteCounts', 'findNoteOffset', 'findNotes',
                           'findNotesMetadata', 'findRelated',
                           'getDefaultNotebook', 'getFilteredSyncChunk',
                           'getLinkedNotebookSyncChunk',
                           'getLinkedNotebookSyncState', 'getNote',
                           'getNoteApplicationData',
                           'getNoteApplicationDataEntry', 'getNoteContent',
                           'getNoteSearchText', 'getNoteTagNames',
                           'getNoteVersion', 'getNotebook', 'getResource',
                           'getResourceAlternateData',
                           'getResourceApplicationData',
                           'getResourceApplicationDataEntry',
                           'getResourceAttributes', 'getResourceByHash',
                           'getResourceData', 'getResourceRecognition',
                           'getResourceSearchText', 'getSearch',
                           'getSharedNotebookByAuth', 'getSyncChunk',
                           'getSyncState', 'getSyncStateWithMetrics', 'getTag',
                           'listLinkedNotebooks', 'listNoteVersions',
                           'listNotebooks', 'listSearches',
                           'listSharedNotebooks', 'listTags',
                           'listTagsByNotebook',
                           'sendMessageToSharedNotebookMembers',
                           'setNoteApplicationDataEntry',
                           'setResourceApplicationDataEntry', 'shareNote',
                           'stopSharingNote', 'unsetNoteApplicationDataEntry',
                           'unsetResourceApplicationDataEntry', 'untagAll',
                           'updateLinkedNotebook', 'updateNote',
                           'updateNotebook', 'updateResource', 'updateSearch',
                           'updateSharedNotebook', 'updateTag']

NON_AUTHENTICATED_API_CALLS = ['getPublicNotebook',]

def to_camel_case(name):
    """Changes pythonic style names to camel case names"""
    return re.sub(r'_([a-z])', lambda pat: pat.group(1).upper(), name)

class EvernoteConnector(object):
    """
    Objects of this class holds a connection to an Evernote account.
    """

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def connect(self):
        """
        Connect to Evernote account, return True if successful, False
        otherwise
        """

        try:
            # Authentication boilerplate
            logging.debug("Authenticating user %s..." % self.username)
            user_store_http_client = THttpClient.THttpClient(EVERNOTE_USER_STORE_URL)
            user_store_protocol = TBinaryProtocol.TBinaryProtocol(user_store_http_client)
            self._userStore = UserStore.Client(user_store_protocol)

            authentication_result = self._userStore.authenticate(self.username, self.password,
                                                                 EVERNOTE_CONSUMER_KEY,
                                                                 EVERNOTE_CONSUMER_SECRET,
                                                                 True)

            if authentication_result.secondFactorRequired:
                code = raw_input("second factor required, please enter your code: ")
                authentication_result = self._userStore.completeTwoFactorAuthentication(authentication_result.authenticationToken,
                                                                                        code,
                                                                                        "Yammer2Hello",
                                                                                        "Yammer 2 Hello Scraper")

            # Gets the authentication token for API calls and note store url
            self.authToken = authentication_result.authenticationToken
            note_store_uri = authentication_result.noteStoreUrl

            # connects to the note store
            logging.debug("Connecting to NoteStore ...")
            note_store_http_client = THttpClient.THttpClient(note_store_uri)
            note_store_procotol = TBinaryProtocol.TBinaryProtocol(note_store_http_client)
            self.note_store = NoteStore.Client(note_store_procotol)

        except EDAMUserException as e:
            logging.fatal('Could not authenticate, please check %s' % e.parameter)
            return False
        except EDAMSystemException as e:
            logging.fatal('System error');
            return False

        return True

    def connect_to_business(self):

        try:
            authentication_result = self._userStore.authenticateToBusiness(self.authToken)

            # Gets the authentication token for API calls and note store url
            self.authToken = authentication_result.authenticationToken
            note_store_uri = authentication_result.noteStoreUrl

            # connects to the note store
            logging.debug("Connecting to NoteStore ...")
            note_store_http_client = THttpClient.THttpClient(note_store_uri)
            note_store_procotol = TBinaryProtocol.TBinaryProtocol(note_store_http_client)
            self.note_store = NoteStore.Client(note_store_procotol)

        except EDAMUserException as e:
            logging.fatal('Could not authenticate, please check %s' % e.parameter)
            return False
        except EDAMSystemException as e:
            logging.fatal('System error');
            return False

        return True

    def __getattr__(self, name):
        camel_case_name = to_camel_case(name)
        if camel_case_name in AUTHENTICATED_API_CALLS:
            def api_call(*args, **kargs):
                return self.note_store.__getattribute__(camel_case_name)(self.authToken, *args, **kargs)
            return api_call
        elif camel_case_name in NON_AUTHENTICATED_API_CALLS:
            def api_call(*args, **kargs):
                return self.note_store.__getattribute__(camel_case_name)(*args, **kargs)
            return api_call
        else:
            raise AttributeError("EvernoteConnector has no attribute %s" % name)

    def get_notebook_by_name(self, name):
        """
        Finds and retrieves the Notebook object from the given name
        """
        notebooks = self.note_store.listNotebooks(self.authToken)
        for notebook in notebooks:
            if notebook.name == name:
                return notebook

    def __repr__(self):
        return "<EvernoteConnector for \"%s\">" % self.username

