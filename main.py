#! /usr/bin/env python
# coding: utf-8

from config import *
from contact import Contact
from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
from evernote.edam.limits.constants import EDAM_USER_NOTES_MAX
from evernote_connector import EvernoteConnector
from getpass import getpass
from optparse import OptionParser
from yammer_connector import YammerConnector
import logging
import sys

def match_notes_and_contacts(ec, notes, contacts):
    """
    If a contact exist as a note, mark the contact's note guid attribute.
    """
    id_notes = {}
    for note in notes:
        if note.attributes.applicationData and 'yammer.id' in note.attributes.applicationData.keysOnly:
            id_notes[int(ec.get_note_application_data_entry(note.guid, 'yammer.id'))] = note

    for contact in contacts:
        if contact.id in id_notes:
            note = id_notes[contact.id]
            contact.note_guid = note.guid

            if note.attributes.applicationData and 'yammer.profile.hash' in note.attributes.applicationData.keysOnly:
                contact.previous_hash = int(ec.get_note_application_data_entry(note.guid, 'yammer.profile.hash'))

if __name__ == "__main__":

    # Set command line parameters
    parser = OptionParser()
    parser.add_option("-u", "--evernote-username", dest="evernote_username",
                      help="The username of the Evernote account", metavar="USERNAME")
    parser.add_option("-p", "--evernote-password", dest="evernote_password",
                      help="The password of the Evernote account", metavar="PASSWORD")
    parser.add_option("-n", "--hello-notebook", dest="hello_notebook",
                      help="The name of the Hello notebook", metavar="NOTEBOOK")
    parser.add_option("-l", "--logging", dest="logging", default=LOG_LEVEL,
                      help="Logging level", metavar="[DEBUG,INFO,WARNING,ERROR,CRITICAL]")
    parser.add_option("-c", "--create-notebook",
                      action="store_true", dest="create_notebook", default=False,
                      help="If notebook is not present, create it")
    parser.add_option("-d", "--dont-update",
                      action="store_true", dest="dont_update", default=False,
                      help="Don't update contact if already present in Hello")
    (options, args) = parser.parse_args()

    # Set logging level
    logging.getLogger().setLevel(options.logging)

    # Connect to evernote
    # Check for required parameters, if not present, ask for them
    if not options.evernote_username:
        options.evernote_username = raw_input("Your Evernote username: ")
    if not options.evernote_password:
        options.evernote_password = getpass("Your Evernote password: ")
    ec = EvernoteConnector(options.evernote_username, options.evernote_password)
    if not ec.connect():
        logging.fatal("Could not connect to Evernote")
        sys.exit(1)


    # Get Hello notes from Evernote
    # Check for required parameter, if not present, ask for it
    if not options.hello_notebook:
        options.hello_notebook = raw_input("Your Hello Notebook name: ")
    notebook = ec.get_notebook_by_name(options.hello_notebook)
    if not notebook:
        if options.create_notebook:
            notebook = ec.create_notebook(options.hello_notebook)
        else:
            # try to connect to business account
            logging.debug("Authenticating to business...")
            if ec.connect_to_business():
                notebook = ec.get_notebook_by_name(options.hello_notebook)
                if not notebook:
                    logging.fatal('Notebook "%s" not found (Personal and Business). If you want it to be created, pass --create-notebook in command line.' %  hello_notebook)
                    sys.exit(1)
            else:
                logging.fatal('Notebook "%s" not found. If you want it to be created, pass --create-notebook in command line.' %  hello_notebook)
                sys.exit(1)

    # get all notes metadata from the notebook
    notes = ec.find_notes_metadata(NoteFilter(notebookGuid=notebook.guid),
                                   0,
                                   EDAM_USER_NOTES_MAX,
                                   NotesMetadataResultSpec(includeAttributes=True)).notes

    # Connect to yammer
    yc = YammerConnector()
    if not yc.connect():
        logging.fatal("Could not connect to Yammer")
        sys.exit(1)

    # get contacts from Yammer
    contacts = list(Contact(user) for user in yc.get_users())

    # Mark contacts that need update and new ones
    match_notes_and_contacts(ec, notes, contacts)

    # For each contact, create new ones, and update which needs update
    for contact in contacts:
        note = contact.to_note()
        note.notebookGuid = notebook.guid
        if note.guid:
            if not options.dont_update and contact.needs_update:
                logging.info("Updating %s" % note.title)
                ec.update_note(note)
        else:
            logging.info("Creating %s" % note.title)
            ec.create_note(note)

