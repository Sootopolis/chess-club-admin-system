from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

import click
import requests

from ..utils.functions import (
    get_existing_members,
    get_player_id_map,
    updated_members_data,
)

from ..utils.structures import (
    Club,
    Configs,
    Member,
    RecordMembers,
)


class _RecordMembersForTracking(RecordMembers):
    def to_cur(self, member: Member):
        member.is_active = True
        self.current.add(member)

    def cur_to_arc(self, member: Member):
        member.is_active = False
        self.archive.add(member)
        self.current.discard(member)

    def arc_to_cur(self, member: Member):
        member.is_active = True
        self.current.add(member)
        self.archive.discard(member)

    def nothing(self, member: Member):
        pass


class _Move(Enum):
    JOINED = auto()
    ARCHIVED = auto()
    RETURNED = auto()
    NOTHING = auto()


@dataclass
class _BaseChangeCategory:
    name: str
    move_method: _Move = _Move.NOTHING


@dataclass
class _Changes(_BaseChangeCategory):
    members: list[Member] = field(default_factory=list, init=False)

    def add_member(self, member: Member):
        self.members.append(member)


@dataclass
class _RenamedChanges(_BaseChangeCategory):
    members: list[tuple[Member, Member]] = field(
        default_factory=list, init=False
    )

    def add_pair(self, old: Member, new: Member):
        self.members.append((old, new))


class _ChangeManager:
    def __init__(self) -> None:
        self.left = _Changes("goners", _Move.ARCHIVED)
        self.joined = _Changes("newbies", _Move.JOINED)
        self.closed = _Changes("closed", _Move.ARCHIVED)
        self.reopened = _Changes("reopened", _Move.RETURNED)
        self.returned = _Changes("returned", _Move.RETURNED)
        self.renamed = _RenamedChanges("renamed")
        # we don't know the new name!
        self.renamed_gone = _Changes("renamed & gone", _Move.ARCHIVED)
        self.renamed_reopened = _RenamedChanges(
            "reopened & renamed", _Move.RETURNED
        )
        self.renamed_returned = _RenamedChanges(
            "renamed & returned", _Move.RETURNED
        )

    @staticmethod
    def _sort_members(changes: _Changes | _RenamedChanges) -> None:
        if isinstance(changes, _Changes):
            changes.members.sort(key=lambda x: x.username)
        else:
            changes.members.sort(key=lambda x: x[1].username)

    @staticmethod
    def _print_changes(changes: _Changes | _RenamedChanges) -> None:
        _ChangeManager._sort_members(changes)
        if len(changes.members) > 0:
            print(changes.name + ":")
            if isinstance(changes, _Changes):
                for member in changes.members:
                    print(member.username, member.url)
            else:
                for old, new in changes.members:
                    print(old.username, "->", new.username, new.url)

    @staticmethod
    def _update_members(changes: _RenamedChanges) -> None:
        for old, new in changes.members:
            old.username = new.username
            old.joined = new.joined

    @staticmethod
    def _get_members(changes: _Changes | _RenamedChanges) -> list[Member]:
        if isinstance(changes, _Changes):
            return changes.members
        else:
            _ChangeManager._update_members(changes)
            return list(map(lambda x: x[0], changes.members))

    @staticmethod
    def _move_members(
        record: _RecordMembersForTracking, changes: _Changes | _RenamedChanges
    ) -> None:
        members = _ChangeManager._get_members(changes)
        match changes.move_method:
            case _Move.JOINED:
                for member in members:
                    record.to_cur(member)
            case _Move.ARCHIVED:
                for member in members:
                    record.cur_to_arc(member)
            case _Move.RETURNED:
                for member in members:
                    record.arc_to_cur(member)
            case _Move.NOTHING:
                for member in members:
                    record.nothing(member)

    @staticmethod
    def _summarise_changes(
        record: _RecordMembersForTracking, changes: _Changes | _RenamedChanges
    ) -> None:
        _ChangeManager._print_changes(changes)
        _ChangeManager._move_members(record, changes)

    def summarise(
        self,
        record: _RecordMembersForTracking,
    ) -> None:
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


def _compare_membership(
    session: requests.Session,
    club_name: str,
    record: _RecordMembersForTracking,
) -> None:
    """compares membership and prints differences,
    outputs list of current and former members"""

    club = Club.from_str(session, club_name)

    incoming = club.get_members(session)

    additions = incoming.difference(record.current)
    deletions = record.current.difference(incoming)

    for new in additions:
        new.update_player_id(session)

    additions_by_id = get_player_id_map(additions)
    archive_by_id = get_player_id_map(record.archive)

    change_manager = _ChangeManager()

    # examining old names that disappeared
    for old in deletions:
        # check if the member is still here by player_id
        if old.player_id in additions_by_id:
            # the member is still here, username or join time or both changed
            new = additions_by_id[old.player_id]
            additions.remove(new)
            # if username is the same, member left and rejoined
            if old.username == new.username:
                old.joined = new.joined
                change_manager.returned.add_member(old)
            # is joined time is the same, member changed username
            elif old.joined == new.joined:
                change_manager.renamed.add_pair(old, new)
            # else both happened
            else:
                old.joined = new.joined
                change_manager.renamed_returned.add_pair(old, new)
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
    for new in additions:
        # check if we have record of this player
        if new.player_id in archive_by_id:
            # we have record of this player
            # if username is the same, the member hasn't renamed
            # if username is different, the member has renamed
            # if join time is the same, the member has reopened
            # if join time is different, the member has returned
            # (in which case we don't case if they closed and reopened)
            old = archive_by_id[new.player_id]
            if old.username == new.username:
                if old.joined == new.joined:
                    change_manager.reopened.add_member(old)
                else:
                    change_manager.returned.add_member(old)
            else:
                if old.joined == new.joined:
                    change_manager.renamed_reopened.add_pair(old, new)
                else:
                    change_manager.renamed_returned.add_pair(old, new)
        else:
            # else this is a completely new member
            change_manager.joined.add_member(new)

    change_manager.summarise(record)


def _compare_and_update_membership(
    session: requests.Session,
    club_name: str,
    readonly: bool = False,
):
    print(
        "checking membership changes"
        + (" without updating record" if readonly else "")
        + f" for {club_name}"
    )
    record = _RecordMembersForTracking(get_existing_members(club_name))
    _compare_membership(session, club_name, record)
    if not readonly:
        updated_members_data(club_name, record)


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
    session = configs.session

    club_names: list[str] = []
    if all_clubs:
        club_names += configs.all_club_names
        print(
            "checking membership changes"
            + (" without updating records" if readonly else "")
            + " for the following club(s):"
        )
        print(*club_names, sep=", ")
    else:
        if club_name:
            club_names.append(club_name)
        elif configs.default_club_name:
            club_names.append(configs.default_club_name)

    if club_names:
        for club_name in club_names:
            _compare_and_update_membership(session, club_name, readonly)
    else:
        print("no club found in configs")
