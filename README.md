# Yammer2Hello

This application connects to Yammer API, grab all your contacts and transform
them into Hello-like Notes in a Notebook of your choice at your Evernote
account.

## Prerequisites

  * Jinja2 (templating engine): http://jinja.pocoo.org/docs/intro/#installation

## Usage

You can pass Evernote username, password and notebook in the command line parameters, or
the application will ask you. For Yammer authentication, please follow the instructions.

    Usage: main.py [options]

    Options:
      -h, --help            show this help message and exit
      -u USERNAME, --evernote-username=USERNAME
                            The username of the Evernote account
      -p PASSWORD, --evernote-password=PASSWORD
                            The password of the Evernote account
      -n NOTEBOOK, --hello-notebook=NOTEBOOK
                            The name of the Hello notebook
      -l [DEBUG,INFO,WARNING,ERROR,CRITICAL], --logging=[DEBUG,INFO,WARNING,ERROR,CRITICAL]
                            Logging level
      -c, --create-notebook
                            If notebook is not present, create it
      -d, --dont-update     Don't update contact if already present in Hello
      
## TODO/Issues

  * A "delete unexistent contacts" option to remove Notes that are no match in Yammer.
  * Currently, this application fetches all Yammer contacts, ignoring "Networks". If one
    has more than a Network, this could be a problem. Also, it exports "inactive" users.
  * Some images are not displaying.
  * Not yet working with Hello app.
  * When updating, sometimes the application creates a duplicated Note contact.


