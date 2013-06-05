#coding: utf-8

from base64 import b64encode
from evernote.edam.type.ttypes import Resource, Note, Data, NoteAttributes, ResourceAttributes, LazyMap
from xml.sax.saxutils import escape
import copy
import hashlib
import jinja2
import logging
import os
import urllib

__all__ = ['Contact']

def make_hash(o):
  """
  Makes a hash of a json like object.
  """
  if isinstance(o, list):
    return hash(tuple(sorted(make_hash(e) for e in o)))
  elif not isinstance(o, dict):
    return hash(o)

  new_o = copy.deepcopy(o)
  for k, v in new_o.items():
    new_o[k] = make_hash(v)

  return hash(tuple(sorted(new_o.items())))

# Load templates
env = jinja2.Environment(loader=jinja2.PackageLoader(__name__, 'templates'), autoescape=True)
hello_template = env.get_template('hello-template.enml')
vcard_template = env.get_template('vcard.vcf')

class Contact(object):
    """
    This is the glue between Yammer and Evernote. It transforms from Yammer
    API's JSON response into Evernote's ENML format. The object is constructed
    with a parsed JSON representing a Yammer user, and the method "to_note"
    returns an Evernote's Note with the user's data.
    """

    def __init__(self, yammer_user_json):
        "Creates a Contact from a parsed JSON Yammer user's object"
        self.user = yammer_user_json
        del self.user['stats']

        # default values
        self.note_guid = None
        self.previous_hash = None
        self.needs_update = True

        # extract some basic info
        self.name = escape(self.user['full_name'])  if 'full_name' in self.user and self.user['full_name'] else ''
        self.id = self.user['id']
        if 'contact' in self.user and 'email_addresses'  in self.user['contact'] and self.user['contact']['email_addresses'] and 'address' in self.user['contact']['email_addresses'][0]:
            self.email = self.user['contact']['email_addresses'][0]['address']
            self.email = escape(self.email) if self.email else ''
        else:
            logging.warn("User %s has no email" % self.name)
            self.email = ''

        # check if the user is active
        self.is_active = 'state' in self.user and self.user['state'] == 'active'

    def __hash__(self):
        return make_hash(self.user)

    def to_vcard(self):
        return vcard_template.render(self.user)

    def to_note(self, encounter=1):
        "Returns an Evernote's Note from this Contact data"

        encoded_name = self.name.encode('utf-8')

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
                                               attributes=ResourceAttributes(fileName="%s.jpg" % encoded_name,
                                                                             attachment=False),
                                               data=resource_data, active=True) )
            else:
                logging.warn("Could not retrieve profile image from %s, response code: %d" % (mugshot_url, u.getcode()))
        else:
            logging.warn("There's not a profile image for user %s" % self.name)

        # Create VCard resource
        vcard_content = self.to_vcard().encode('utf-8')
        vcard_hash = hashlib.md5(vcard_content)
        self.user['vcard_hash'] = vcard_hash.hexdigest()
        resource_list.append( Resource(mime='text/vcard', active=True,
                                       attributes=ResourceAttributes(fileName="%s.vcf" % encoded_name,
                                                                     attachment=True),
                                       data=Data(size=len(vcard_content),
                                                 bodyHash=vcard_hash.digest(),
                                                 body=vcard_content)) )

        # calculate hash and determine if the contact needs update
        current_hash = hash(self)
        self.needs_update = current_hash != self.previous_hash

        # Create note and return
        note_content = hello_template.render(self.user).encode('utf-8')
        application_data = LazyMap(fullMap={'yammer.id': str(self.user['id']),
                                            'yammer.profile.hash': str(current_hash)})
        note = Note(guid=self.note_guid,
                    title=encoded_name,
                    content=note_content, active=True, resources=resource_list,
                    attributes=NoteAttributes(contentClass='evernote.hello.encounter.%d' % encounter,
                                              applicationData=application_data))

        return note

    def __getattr__(self, name):
        return self.user[name]

