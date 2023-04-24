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
    ChangeManager,
    RecordMembersForTracking,
)


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
    record = get_existing_members(configs.club.url_name)
    compare_membership(configs.session, configs.club, record)
    if not readonly:
        updated_members_data(configs.club.url_name, record)
