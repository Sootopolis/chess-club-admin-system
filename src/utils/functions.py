import re
from typing import Iterable, Optional

from .csv_utils import get_existing_members_from_csv, update_members_csv
from .structures import Configs, Member, MemberRecords


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


def validate_email(email: str) -> bool:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if re.match(pattern, email):
        return True
    else:
        return False


def get_club_name(configs: Configs, club_name: Optional[str] = None) -> str:
    if club_name:
        if club_name not in configs.all_club_names:
            raise SystemExit(
                f'"{club_name}" is not in `configs.yml` - '
                "use `ccas config add-club` to add the club."
            )
        return club_name
    elif configs.default_club_name:
        return configs.default_club_name
    else:
        raise SystemExit("no club configured")
