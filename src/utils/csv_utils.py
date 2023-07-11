import csv
import os

from .structures import Member, MemberRecords

DIR = "CSV_files/{}"
PATH = f"{DIR}/members.csv"
HEADER = ("username", "player_id", "joined", "is_active")


def get_existing_members_from_csv(club_name: str) -> list[Member]:
    members: list[Member] = []
    try:
        with open(PATH.format(club_name)) as stream:
            reader = csv.reader(stream)
            next(reader)
            for row in reader:
                member = Member(
                    username=row[0],
                    player_id=int(row[1]),
                    joined=int(row[2]),
                    is_active=bool(int(row[3])),
                )
                if member.username and member.player_id and member.joined:
                    members.append(member)
    except FileNotFoundError:
        print(f"error getting file from {PATH.format(club_name)}")
    return members


def update_members_csv(club_name: str, record: MemberRecords) -> None:
    members = sorted(record.all, key=lambda x: (not x.is_active, x.username))
    dir = DIR.format(club_name)
    if not os.path.exists(dir):
        os.makedirs(dir)
    with open(PATH.format(club_name), "w", newline="\n") as stream:
        writer = csv.writer(stream)
        writer.writerow(HEADER)
        for member in members:
            username = member.username
            player_id = str(member.player_id) if member.player_id else "0"
            joined = str(member.joined) if member.joined else "0"
            is_active = "1" if member.is_active else "0"
            writer.writerow((username, player_id, joined, is_active))
