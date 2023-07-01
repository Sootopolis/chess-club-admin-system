from dataclasses import dataclass, field
from typing import Optional

import click
import requests

from ..utils.functions import (
    get_member_records,
    get_player_id_map,
    updated_members_data,
)

from ..utils.structures import (
    Club,
    Configs,
    Member,
    MemberRecords,
)


@dataclass
class _BaseChangeCategory:
    name: str
    active: Optional[bool] = None
    members: list = field(default_factory=list)


@dataclass
class _Changes(_BaseChangeCategory):
    members: list[Member] = field(default_factory=list)

    def add_member(self, member: Member) -> None:
        self.members.append(member)

    def sort_members(self) -> None:
        self.members.sort()

    def print_changes(self) -> None:
        if self.members:
            print(f"{self.name} ({len(self.members)}):")
            for member in self.members:
                print(member.username, member.url)

    def get_members(self) -> list[Member]:
        return self.members


@dataclass
class _Returners(_BaseChangeCategory):
    pairs: list[tuple[Member, Member]] = field(default_factory=list)

    def add_pair(self, old: Member, new: Member) -> None:
        self.pairs.append((old, new))

    def sort_members(self) -> None:
        self.pairs.sort(key=lambda x: x[1])

    def print_changes(self) -> None:
        if self.pairs:
            print(f"{self.name} ({len(self.pairs)}):")
            for old, new in self.pairs:
                if old.username != new.username:
                    print(old.username, "->", new.username, new.url)
                else:
                    print(old.username, old.url)

    def _update_members(self) -> None:
        for old, new in self.pairs:
            old.username = new.username
            old.joined = new.joined

    def get_members(self) -> list[Member]:
        self._update_members()
        return [pair[0] for pair in self.pairs]


class _ChangeManager:
    def __init__(self) -> None:
        self.left = _Changes("goners", False)
        self.closed = _Changes("closed", False)
        self.joined = _Changes("newbies", True)
        self.reopened = _Changes("reopened", True)
        self.returned = _Returners("returned", True)
        self.renamed = _Returners("renamed", None)
        # we don't know the new name!
        self.renamed_gone = _Changes("renamed & gone", False)
        self.renamed_reopened = _Returners("reopened & renamed", True)
        self.renamed_returned = _Returners("renamed & returned", True)

    @staticmethod
    def _update_records(
        record: MemberRecords, changes: _Changes | _Returners
    ) -> None:
        members: list[Member] = changes.get_members()
        if changes.active is not None:
            record.update(members, changes.active)

    @staticmethod
    def _summarise_changes(
        record: MemberRecords, changes: _Changes | _Returners
    ) -> None:
        changes.sort_members()
        changes.print_changes()
        _ChangeManager._update_records(record, changes)

    def summarise(self, record: MemberRecords) -> None:
        for changes in (
            self.left,
            self.joined,
            self.closed,
            self.reopened,
            self.returned,
            self.renamed,
            self.renamed_gone,
            self.renamed_reopened,
            self.renamed_returned,
        ):
            _ChangeManager._summarise_changes(record, changes)
        print(f"total: {len(record.current)}")


def _get_id_maps(
    session: requests.Session, club: Club, record: MemberRecords
) -> tuple[dict[int, Member], dict[int, Member]]:
    existing_set = set(record.current.values())
    incoming_set = set(club.get_members(session))
    additions_set = incoming_set.difference(existing_set)
    deletions_set = existing_set.difference(incoming_set)
    for member in additions_set:
        member.update_player_id(session)
    additions_by_id = get_player_id_map(additions_set)
    deletions_by_id = get_player_id_map(deletions_set)
    return additions_by_id, deletions_by_id


def _compare(
    session: requests.Session, club_name: str, record: MemberRecords
) -> None:
    """compares membership and prints differences,
    outputs list of current and former members"""

    club = Club.from_str(session, club_name)
    change_manager = _ChangeManager()
    additions_by_id, deletions_by_id = _get_id_maps(session, club, record)

    # examining old names that disappeared
    for old_id in deletions_by_id:
        old = deletions_by_id[old_id]
        # check if the member is still here by player_id
        if old_id in additions_by_id:
            # the member is still here, username or join time or both changed
            new = additions_by_id[old_id]
            # if username is the same, member left and rejoined
            if old.username == new.username:
                change_manager.returned.add_pair(old, new)
            # is joined time is the same, member changed username
            elif old.joined == new.joined:
                change_manager.renamed.add_pair(old, new)
            # else both happened
            else:
                change_manager.renamed_returned.add_pair(old, new)
            del additions_by_id[old_id]
        else:
            # the member is gone
            try:
                # if api is accessible, check if player is still in the club
                if club.url in old.get_club_urls(session):
                    # if so, the account is closed
                    change_manager.closed.add_member(old)
                else:
                    # else the member is gone
                    change_manager.left.add_member(old)
            except requests.exceptions.HTTPError:
                # member renamed and either left or closed - we can't tell
                change_manager.renamed_gone.add_member(old)

    # examining the remaining new names
    for new_id in additions_by_id:
        new = additions_by_id[new_id]
        # check if we have record of this player
        if new_id in record.archive:
            # we have record of this player
            # if username is the same, the member hasn't renamed
            # if username is different, the member has renamed
            # if join time is the same, the member has reopened
            # if join time is different, the member has returned
            # (in which case we don't case if they closed and reopened)
            old = record.archive[new_id]
            if old.username == new.username:
                if old.joined == new.joined:
                    change_manager.reopened.add_member(old)
                else:
                    change_manager.returned.add_pair(old, new)
            else:
                if old.joined == new.joined:
                    change_manager.renamed_reopened.add_pair(old, new)
                else:
                    change_manager.renamed_returned.add_pair(old, new)
        else:
            # else this is a completely new member
            change_manager.joined.add_member(new)

    change_manager.summarise(record)


def _compare_and_update(
    session: requests.Session, club_name: str, readonly: bool = False
):
    print(
        "checking membership changes"
        + (" without updating record" if readonly else "")
        + f" for {club_name}"
    )
    record = get_member_records(club_name)
    _compare(session, club_name, record)
    if not readonly:
        updated_members_data(club_name, record)


def _get_club_names(
    configs: Configs,
    club_name: Optional[str] = None,
    all_clubs: bool = False,
    readonly: bool = False,
):
    if all_clubs:
        print(
            "checking membership changes"
            + (" without updating records" if readonly else "")
            + " for the following club(s):"
        )
        print(*configs.all_club_names, sep=", ")
        return configs.all_club_names
    elif club_name:
        if club_name not in configs.all_club_names:
            raise SystemExit(
                f'club "{club_name}" is not in `configs.yml` - '
                "use `ccas config add-club` to add the club."
            )
        return [club_name]
    else:
        return [configs.default_club_name]


@click.command()
@click.option("--club-name", "-c")
@click.option("--all-clubs", "-a", is_flag=True, default=False)
@click.option("--readonly", "-r", is_flag=True, default=False)
def membership(
    club_name: Optional[str] = None,
    all_clubs: bool = False,
    readonly: bool = False,
) -> None:
    if club_name and all_clubs:
        message = "`membership()` cannot take both `club_name` and `all_clubs`"
        raise SystemExit(message)

    configs = Configs.from_yaml()

    club_names = _get_club_names(configs, club_name, all_clubs, readonly)

    if club_names:
        for name in club_names:
            _compare_and_update(configs.session, name, readonly)
    else:
        print("no club found in configs")
