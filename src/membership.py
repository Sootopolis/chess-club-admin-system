from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

import click
import requests

from .functions import (
    get_existing_members,
    get_player_id_map,
    updated_members_data,
)
from .structures import (
    Club,
    Configs,
    Member,
    RecordMembers,
)


class RecordMembersForTracking(RecordMembers):
    def to_cur(self, member: Member):
        assert not (member in self.current or member in self.archive)
        member.is_active = True
        self.current.add(member)

    def cur_to_arc(self, member: Member):
        assert member in self.current and member in self.archive
        member.is_active = False
        self.archive.add(member)
        self.current.remove(member)

    def arc_to_cur(self, member: Member):
        assert member in self.current and member in self.archive
        member.is_active = True
        self.current.add(member)
        self.archive.remove(member)

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


class ChangeManager:
    left = _Changes("goners", _Move.ARCHIVED)
    joined = _Changes("newbies", _Move.JOINED)
    closed = _Changes("closed", _Move.ARCHIVED)
    reopened = _Changes("reopened", _Move.RETURNED)
    returned = _Changes("returned", _Move.RETURNED)
    renamed = _RenamedChanges("renamed")
    # we don't know the new name!
    renamed_gone = _Changes("renamed & gone", _Move.ARCHIVED)
    renamed_reopened = _RenamedChanges("reopened & renamed", _Move.RETURNED)
    renamed_returned = _RenamedChanges("renamed & returned", _Move.RETURNED)

    @staticmethod
    def _sort_members(changes: _Changes | _RenamedChanges):
        if isinstance(changes, _Changes):
            changes.members.sort(key=lambda x: x.username)
        else:
            changes.members.sort(key=lambda x: x[1].username)

    @staticmethod
    def _print_changes(changes: _Changes | _RenamedChanges):
        ChangeManager._sort_members(changes)
        if len(changes.members) > 0:
            print(changes.name)
            if isinstance(changes, _Changes):
                for member in changes.members:
                    print(member.username, member.url)
            else:
                for old, new in changes.members:
                    print(old.username, "->", new.username, new.url)

    @staticmethod
    def _update_members(changes: _RenamedChanges):
        for old, new in changes.members:
            old.username = new.username
            old.joined = new.joined

    @staticmethod
    def _get_members(changes: _Changes | _RenamedChanges):
        if isinstance(changes, _Changes):
            return changes.members
        else:
            ChangeManager._update_members(changes)
            return list(map(lambda x: x[0], changes.members))

    @staticmethod
    def _move_members(
        record: RecordMembersForTracking, changes: _Changes | _RenamedChanges
    ):
        members = ChangeManager._get_members(changes)
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
        record: RecordMembersForTracking, changes: _Changes | _RenamedChanges
    ):
        ChangeManager._print_changes(changes)
        ChangeManager._move_members(record, changes)

    def summarise(
        self,
        record: RecordMembersForTracking,
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
            ChangeManager._summarise_changes(record, changes)
        print(f"total: {len(record.current)}")


def compare_membership(
    session: requests.Session, club: Club, record: RecordMembersForTracking
) -> None:
    """compares membership and prints differences,
    outputs list of current and former members"""

    incoming = club.get_members(session)

    additions = incoming.difference(record.current)
    deletions = record.current.difference(incoming)

    for new in additions:
        new.update_player_id(session)

    additions_by_id = get_player_id_map(additions)
    archive_by_id = get_player_id_map(record.archive)

    changes = ChangeManager()

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
                changes.returned.add_member(old)
            # is joined time is the same, member changed username
            elif old.joined == new.joined:
                changes.renamed.add_pair(old, new)
            # else both happened
            else:
                old.joined = new.joined
                changes.renamed_returned.add_pair(old, new)
        else:
            # the member is gone
            try:
                # if api is accessible, check if player is still in the club
                if club.url in old.get_club_urls(session):
                    # if so, the account is closed
                    changes.closed.add_member(old)
                else:
                    # else the member is gone
                    changes.left.add_member(old)
            except requests.exceptions.HTTPError:
                # member renamed and either left or closed - we can't tell
                changes.renamed_gone.add_member(old)

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
                    changes.reopened.add_member(old)
                else:
                    changes.returned.add_member(old)
            else:
                if old.joined == new.joined:
                    changes.renamed_reopened.add_pair(old, new)
                else:
                    changes.renamed_returned.add_pair(old, new)
        else:
            # else this is a completely new member
            changes.joined.add_member(new)

    changes.summarise(record)


@click.command()
@click.option("--club-name", "-c")
@click.option("--readonly", "-r", is_flag=True, default=False)
def membership(
    club_name: Optional[str] = None, readonly: bool = False
) -> None:
    configs = Configs.get_configs(club_name)
    record = RecordMembersForTracking(
        get_existing_members(configs.club.url_name)
    )
    compare_membership(configs.session, configs.club, record)
    if not readonly:
        updated_members_data(configs.club.url_name, record)
