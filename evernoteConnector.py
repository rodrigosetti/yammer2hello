# coding: utf-8

import logging
from evernote.edam.error.ttypes import EDAMUserException, EDAMSystemException
from evernote.edam.notestore.ttypes import NoteFilter
from evernote.edam.type.ttypes import NoteSortOrder
import evernote.edam.notestore.NoteStore as NoteStore
import evernote.edam.userstore.UserStore as UserStore
import thrift.protocol.TBinaryProtocol as TBinaryProtocol
import thrift.transport.THttpClient as THttpClient
from config import *

__all__ = ['EvernoteConnector', 'Notebook', 'Note']

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
            userStoreHTTPClient = THttpClient.THttpClient('https://www.evernote.com/edam/user')
            userStoreProtocol = TBinaryProtocol.TBinaryProtocol(userStoreHTTPClient)
            self._userStore = UserStore.Client(userStoreProtocol)

            authentication_result = self._userStore.authenticate(self.username, self.password,
                                                                 EVERNOTE_CONSUMER_KEY, EVERNOTE_CONSUMER_SECRET)

            # Gets the authentication token for API calls and note store url
            self.authToken = authentication_result.authenticationToken
            noteStoreURI = authentication_result.noteStoreUrl

            # connects to the note store
            logging.debug("Connecting to NoteStore ...")
            noteStoreHTTPClient = THttpClient.THttpClient(noteStoreURI)
            noteStoreProtocol = TBinaryProtocol.TBinaryProtocol(noteStoreHTTPClient)
            self.noteStore = NoteStore.Client(noteStoreProtocol)
        except EDAMUserException as e:
            logging.fatal('Could not authenticate, please check %s' % e.parameter)
            return False
        except EDAMSystemException as e:
            logging.fatal('System error');
            return False

        return True

    def getNotebookByName(self, notebookName):
        notebooks = self.noteStore.listNotebooks(self.authToken)
        for notebook in notebooks:
            if notebook.name == notebookName:
                return Notebook(notebook, self.noteStore, self.authToken)

    def __repr__(self):
        return "<EvernoteConnector for \"%s\">" % self.username


class Notebook(object):
    """
    Wrapper to the Notebook thrift object, to make it more object oriented
    """

    def __init__(self, notebook=None, noteStore=None, authToken=None):
        self.__dict__["notebook"] = notebook
        self.__dict__["noteStore"] = noteStore
        self.__dict__["authToken"] = authToken

    def getNotes(self):
        noteFilter = NoteFilter()
        noteFilter.notebookGuid = self.__dict__["notebook"].guid
        noteList = self.noteStore.findNotes(self.__dict__["authToken"], noteFilter, 0, int(MAX_NOTES))
        return [Note(note, self.__dict__["noteStore"], self.__dict__["authToken"]) for note in noteList.notes]

    def createNote(self, note):
        note.notebookGuid = self.__dict__["notebook"].guid
        newNote = self.noteStore.createNote(self.__dict__["authToken"], note)
        return Note(newNote, self.__dict__["noteStore"], self.__dict__["authToken"])

    def __getattr__(self, name):
        return self.notebook.__dict__[name]

    def __setattr__(self, name, value):
        self.notebook.__dict__[name] = value
        return self

class Note(object):
    """
    Wrapper to the Notebook thrift object, to make it more object oriented
    """

    def __init__(self, note=None, noteStore=None, authToken=None):
        self.__dict__["note"] = note
        self.__dict__["noteStore"] = noteStore
        self.__dict__["authToken"] = authToken

    def getContent(self):
        if self.content:
            return self.content
        else:
            self.content = self.noteStore.getNoteContent(self.__dict__["authToken"], self.__dict__["note"].guid)
            return self.content

    def update(self, note=None):
        if note:
            note.guid = self.guid
        else:
            note = self.__dict__["note"]
        return self.noteStore.updateNote(self.__dict__["authToken"], note)

    def __getattr__(self, name):
        return self.note.__dict__[name]

    def __setattr__(self, name, value):
        self.note.__dict__[name] = value
        return self

