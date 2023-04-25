from typing import Iterable

import requests
from .structures import ClubConfig, Member, RecordMembers
from .csv_utils import get_existing_members_from_csv, update_members_csv


def get_session(configs: ClubConfig):
    session = requests.session()
    session.headers.update(configs.http_header)
    return session


# this allows for seamless transition from csv to database
def get_existing_members(club_url_name: str) -> list[Member]:
    return get_existing_members_from_csv(club_url_name)


# this allows for seamless transition from csv to database
def updated_members_data(club_url_name: str, record: RecordMembers):
    return update_members_csv(club_url_name, record)


def get_player_id_map(members: Iterable[Member]) -> dict[int, Member]:
    player_id_map: dict[int, Member] = {}
    for member in members:
        if member.player_id:
            player_id_map[member.player_id] = member
    return player_id_map
