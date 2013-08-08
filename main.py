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

def find_all_notes_metadata(ec, note_filter, result_spec):
    """Return a generator that yields NoteMetadata objects for all notes with the
    given filter.

    Args:
      note_filter -
        The NoteFilter object.
      result_spec -
        A NoteStore.NotesMetadataResultSpec object detailing which fields the
        resulting NoteMetadata objects should contain.

    Yields:
      A NoteMetadata object for each note that satisfies the filter.
    """
    offset = 0
    notes_page_size = 200

    while True:
        notes = ec.find_notes_metadata(note_filter, offset=offset,
                                       maxNotes=notes_page_size,
                                       resultSpec=result_spec)

        for note_md in notes.notes:
            yield note_md

        offset = offset + len(notes.notes)
        if offset >= notes.totalNotes:
            break

def match_notes_and_contacts(ec, notes, contacts):
    """
    If a contact exist as a note, mark the contact's note guid attribute.
    """
    id_notes = {}
    for note in notes:
        if note.attributes.applicationData and 'yammer.id' in note.attributes.applicationData.keysOnly:
            id_notes[int(ec.get_note_application_data_entry(note.guid, 'yammer.id'))] = note
        else:
            print "Does not have yammer.id:", note.title

    for contact in contacts:
        if contact.id in id_notes:
            note = id_notes[contact.id]
            del id_notes[contact.id]
            contact.note_guid = note.guid

            note_2 = ec.get_note(note.guid, False, False, False, False)     #
            contact.got_image = len(note_2.resources) >= 2                  #

#            if note.attributes.applicationData and 'yammer.profile.hash' in note.attributes.applicationData.keysOnly:
#                contact.note_content_hash = int(ec.get_note_application_data_entry(note.guid, 'yammer.profile.hash'))

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
    logging.debug("Downloading notes metadata...")
    notes = list(find_all_notes_metadata(ec, NoteFilter(notebookGuid=notebook.guid),
                                         NotesMetadataResultSpec(includeAttributes=True,
                                                                 includeLargestResourceMime=True)))

    # Connect to yammer
    logging.debug("Connecting to Yammer...")
    yc = YammerConnector()
    if not yc.connect():
        logging.fatal("Could not connect to Yammer")
        sys.exit(1)

    # get contacts from Yammer
    logging.debug("Downloading Yammer contacts...")
    contacts = list(Contact(user) for user in yc.get_users())

    # Mark contacts that need update and new ones
    logging.debug("Checking which notes needs update...")
    match_notes_and_contacts(ec, notes, contacts)

    # For each contact, create new ones, and update which needs update
    logging.debug("Uploading notes to Evernote...")
    for contact in contacts:
        note = contact.to_note()
        note.notebookGuid = notebook.guid
        if note.guid:
#            if not options.dont_update and contact.needs_update:
            if not contact.got_image:
                logging.info("Updating %s" % note.title)
#                ec.update_note(note)
        else:
            logging.info("Creating %s" % note.title)
#            ec.create_note(note)

