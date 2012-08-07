#! /usr/bin/env python
# coding: utf-8

def findNoteForContact(notes, contact):
    for note in notes:
        content = note.getContent()
        if contact.name in content or contact.email in content:
            return note

    return None

if __name__ == "__main__":
    from config import *
    from contact import Contact
    from evernoteConnector import EvernoteConnector
    from getpass import getpass
    from optparse import OptionParser
    from yammerConnector import YammerConnector
    import logging
    import sys

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
    notebook = ec.getNotebookByName(options.hello_notebook)
    if not notebook:
        if options.create_notebook:
            notebook = ec.createNotebook(options.hello_notebook)
        else:
            logging.fatal('Notebook "%s" not found. If you want it to be created, pass --create-notebook in command line.' %  hello_notebook)
            sys.exit(1)

    notes = notebook.getNotes()

    # Connect to yammer
    yc = YammerConnector()
    if not yc.connect():
        logging.fatal("Could not connect to Yammer")
        sys.exit(1)

    # get contacts from Yammer
    contacts = (Contact(user) for user in yc.getUsers())

    # Check for every Yammer contact, if there's not contained
    # in hello's notebook. If not, create a new note for contact
    for contact in contacts:
        note = findNoteForContact(notes, contact)
        if note and not options.dont_update:
            logging.info("Updating %s..." % contact.name)
            note.update(contact.toNote())
        else:
            logging.info("Creating note for %s..." % contact.name)
            notebook.createNote(contact.toNote())

