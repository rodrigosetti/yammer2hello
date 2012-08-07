#coding: utf-8

from evernote.edam.type.ttypes import Resource, Note, Data
from string import Template
from xml.sax.saxutils import escape
import hashlib
import os
import urllib

__all__ = ['Contact']

class Contact(object):

    def __init__(self, yammerUserJsonObject):
        self.user = yammerUserJsonObject

        # extract some basic info
        self.name = escape(self.user['full_name'])  if 'full_name' in self.user and self.user['full_name'] else ''
        if 'contact' in self.user and 'email_addresses'  in self.user['contact'] and self.user['contact']['email_addresses'] and 'adress' in self.user['contact']['email_addresses'][0]:
            self.email = self.user['contact']['email_addresses'][0]['adress']
            self.email = escape(self.email) if self.email else ''
        else:
            self.email = ''

        # load ENML file template
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'hello-template.enml')) as f:
            self.helloTemplate = f.read()

    def toNote(self):

        params = {}

        params['display_as'] = self.name
        params['email'] = self.email
        params['given_name'] = escape(self.user['first_name'])  if 'first_name' in self.user and self.user['first_name'] else ''
        params['family_name'] = escape(self.user['last_name'])  if 'last_name' in self.user and self.user['last_name'] else ''
        params['place_address'] = escape(self.user['location'])  if 'location' in self.user and self.user['location'] else ''

        if 'contact' in self.user and 'phone_numbers'  in self.user['contact'] and self.user['contact']['phone_numbers'] and 'number' in self.user['contact']['phone_numbers'][0]:
            params['phone'] = self.user['contact']['phone_numbers'][0]['number']
            params['phone'] = escape(params['phone']) if params['phone'] else ''
        else:
            params['phone'] = ''

        # Load resources
        resource_list = []
        if 'mugshot_url_template' in self.user:
            url_template = self.user['mugshot_url_template']
            mugshot_url = url_template.replace('{width}', '300').replace('{height}', '300')
            u = urllib.urlopen(mugshot_url)

            if u.getcode() == 200:
                # find out resource mime type
                params['profile_image_mime'] = u.headers['content-type']  if 'content-type' in u.headers else 'image/png'

                # Create Resource data
                image_data = u.read()
                image_hash = hashlib.md5(image_data)
                params['profile_image_hash'] = image_hash.hexdigest()
                resource_data = Data(size=len(image_data), bodyHash=image_hash.digest(), body=image_data)

                # append resource to resources list
                resource_list.append( Resource(width=300, height=300, mime=params['profile_image_mime'], data=resource_data, active=True) )

        # Create note and return
        s = Template(self.helloTemplate).substitute(params)
        note_content = s.encode('utf-8', errors='ignore')
        #note_content = Template(self.helloTemplate).substitute(params).decode('utf-8', errors='ignore')
        return Note(title=params['display_as'], content=note_content, active=True, resources=resource_list)

    def __getattr__(self, name):
        return self.user.__getattr__(name)

