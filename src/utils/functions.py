from typing import Iterable

from .structures import Member, MemberRecords
from .csv_utils import get_existing_members_from_csv, update_members_csv


# this allows for seamless transition from csv to database
def get_existing_members(club_name: str) -> list[Member]:
    return get_existing_members_from_csv(club_name)


def get_member_records(club_name: str) -> MemberRecords:
    return MemberRecords(get_existing_members(club_name))


# this allows for seamless transition from csv to database
def updated_members_data(club_name: str, record: MemberRecords):
    return update_members_csv(club_name, record)


def get_player_id_map(members: Iterable[Member]) -> dict[int, Member]:
    player_id_map: dict[int, Member] = {}
    for member in members:
        if member.player_id:
            player_id_map[member.player_id] = member
    return player_id_map


def get_username_map(members: Iterable[Member]) -> dict[str, Member]:
    username_map: dict[str, Member] = {}
    for member in members:
        username_map[member.username] = member
    return username_map
