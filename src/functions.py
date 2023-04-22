import requests
from .structures import Configs, Member
from .csv_utils import get_existing_members_from_csv, update_members_csv


def get_session(configs: Configs):
    session = requests.session()
    session.headers.update(configs.http_header)
    return session


# this allows for seamless transition from csv to database
def get_existing_members(club_url_name: str):
    return get_existing_members_from_csv(club_url_name)


# this allows for seamless transition from csv to database
def updated_members_data(club_url_name: str, members: list[Member]):
    return update_members_csv(club_url_name, members)
