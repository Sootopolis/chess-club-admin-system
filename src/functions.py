import requests

from structures import Club


def compare_membership(session: requests.Session, club: Club):
    incoming = club.get_members(session)
    print(incoming)
