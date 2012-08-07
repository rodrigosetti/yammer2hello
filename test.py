
import yammerConnector
import os

yc = yammerConnector.YammerConnector()
yc.connect()

users = yc.getUsers()

print users.next()

