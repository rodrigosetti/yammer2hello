#coding: utf-8

from base64 import b64encode
from evernote.edam.type.ttypes import Resource, Note, Data, NoteAttributes, ResourceAttributes
from string import Template
from xml.sax.saxutils import escape
import hashlib
import jinja2
import logging
import os
import urllib

__all__ = ['Contact']

class Contact(object):
    """
    This is the glue between Yammer and Evernote. It transforms from Yammer
    API's JSON response into Evernote's ENML format. The object is constructed
    with a parsed JSON representing a Yammer user, and the method "toNote"
    returns an Evernote's Note with the user's data.
    """

    def __init__(self, yammerUserJsonObject):
        "Creates a Contact from a parsed JSON Yammer user's object"
        self.user = yammerUserJsonObject

        # extract some basic info
        self.name = escape(self.user['full_name'])  if 'full_name' in self.user and self.user['full_name'] else ''
        if 'contact' in self.user and 'email_addresses'  in self.user['contact'] and self.user['contact']['email_addresses'] and 'address' in self.user['contact']['email_addresses'][0]:
            self.email = self.user['contact']['email_addresses'][0]['address']
            self.email = escape(self.email) if self.email else ''
        else:
            logging.warn("User %s has no email" % self.name)
            self.email = ''

        # Load file template
        env = jinja2.Environment(loader=jinja2.PackageLoader(__name__, 'templates'), autoescape=True)
        self.helloTemplate = env.get_template('hello-template.enml')
        self.vcardTemplate = env.get_template('vcard.vcf')

    def toVCard(self):
        return self.vcardTemplate.render(self.user)

    def toNote(self):
        "Returns an Evernote's Note from this Contact data"

        # Load resources
        resource_list = []
        if 'mugshot_url_template' in self.user:
            url_template = self.user['mugshot_url_template']
            mugshot_url = url_template.replace('{width}', '300').replace('{height}', '300')
            u = urllib.urlopen(mugshot_url)

            if u.getcode() == 200:
                # find out resource mime type
                self.user['profile_image_mime'] = u.headers['content-type'].lower() if 'content-type' in u.headers else 'image/png'

                # Create Resource data
                image_data = u.read()
                image_hash = hashlib.md5(image_data)
                self.user['profile_image_hash'] = image_hash.hexdigest()
                resource_data = Data(size=len(image_data), bodyHash=image_hash.digest(), body=image_data)

                # put a base64 encoded text of the image content
                self.user['photo_base64'] = b64encode(image_data)

                # append resource to resources list
                resource_list.append( Resource(width=300, height=300,
                                               mime=self.user['profile_image_mime'],
                                               attributes=ResourceAttributes(fileName="%s.jpg" % self.name, attachment=False),
                                               data=resource_data, active=True) )
            else:
                logging.warn("Could not retrieve profile image from %s, response code: %d" % (mugshot_url, u.getcode()))
        else:
            logging.warn("There's not a profile image for user %s" % self.name)

        # Create VCard resource
        vcard_content = self.toVCard()
        vcard_hash = hashlib.md5(vcard_content)
        self.user['vcard_hash'] = vcard_hash.hexdigest()
        resource_list.append( Resource(mime='text/vcard', active=True,
                                       attributes=ResourceAttributes(fileName="%s.vcf" % self.name, attachment=True),
                                       data=Data(size=len(vcard_content),
                                                 bodyHash=vcard_hash.digest(),
                                                 body=vcard_content)) )

        # Create note and return
        note_content = self.helloTemplate.render(self.user).encode('utf-8', errors='ignore')
        note = Note(title=self.name, content=note_content, active=True, resources=resource_list,
                    attributes=NoteAttributes(contentClass='evernote.hello.encounter.2'))

        return note

    def __getattr__(self, name):
        return self.user[name]

