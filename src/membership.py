from typing import Iterable
import requests

from .functions import get_existing_members, updated_members_data
from .structures import Club, Member, MembershipChanges


def get_player_id_map(members: Iterable[Member]) -> dict[int, Member]:
    player_id_map: dict[int, Member] = {}
    for member in members:
        if member.player_id:
            player_id_map[member.player_id] = member
    return player_id_map


def compare_membership(session: requests.Session, club: Club) -> list[Member]:
    """compares membership and prints differences,
    outputs list of current and former members"""

    incoming = club.get_members(session)
    existing = get_existing_members(club.url_name)

    additions = incoming.difference(existing.current)
    deletions = existing.current.difference(incoming)

    for new in additions:
        new.update_player_id(session)

    additions_by_id = get_player_id_map(additions)
    archive_by_id = get_player_id_map(existing.archive)

    changes = MembershipChanges()

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
                changes.returned.append(old)
            # is joined time is the same, member changed username
            elif old.joined == new.joined:
                changes.renamed.append((old, new))
            # else both happened
            else:
                old.joined = new.joined
                changes.renamed_returned.append((old, new))
        else:
            # the member is gone
            try:
                # if api is accessible, check if player is still in the club
                if club.url in old.get_club_urls(session):
                    # if so, the account is closed
                    changes.closed.append(old)
                else:
                    # else the member is gone
                    changes.left.append(old)
            except requests.exceptions.HTTPError:
                # member renamed and either left or closed - we can't tell
                changes.renamed_gone.append(old)

    # examining the remaining new names
    for new in additions:
        # check if we have record of this player
        if new.player_id in archive_by_id:
            # if we do, the player renamed or returned or both
            old = archive_by_id[new.player_id]
            # the renamed case should've been handled earlier!
            assert new.joined != old.joined
            if new.username == old.username:
                changes.returned.append(old)
            else:
                changes.renamed_returned.append((old, new))
        else:
            # else this is a completely new member
            changes.joined.append(new)

    changes.summarise(existing)

    return sorted(existing.current | existing.archive)


def update_membership(
    session: requests.Session, club: Club, readonly: bool = False
) -> None:
    members = compare_membership(session, club)
    if not readonly:
        updated_members_data(club.url_name, members)
