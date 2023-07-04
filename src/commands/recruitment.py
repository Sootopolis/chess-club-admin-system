from typing import Optional

import click

from ..utils.functions import get_club_name
from ..utils.structures import Club, Configs
from .membership import membership

"""
0. get parameters
0.1. club name (optional)
0.1.1. warn if club is not in config (or club doesn't have membership record)
0.2. target club name (optional)

1. run `membership`

2. get local record
2.1. get local membership record
2.2. get local candidates record

3. get list of target clubs
3.1. from command line input
3.2. from config file

for each target club:

4. get target club information
4.1. get list of target club members
4.2. get list of target club admins

5. initial filtering of candidates based on username
5.1. eliminate existing members
5.2. eliminate checked candidates
5.3. eliminate club admins
5.4. eliminate no-nos

for each candidate:

6. secondary filtering of candidates

6.1. get candidate profile
6.1.1. reinforced initial filtering based on player_id
6.1.2. eliminate if last online is too long ago per config
6.1.3. eliminate if country doesn't match per config

6.2. get candidate clubs
6.2.1. eliminate if candidate is in too many clubs per config
6.2.1. eliminate if candidate is in certain clubs per config

6.3. get candidate stats
6.3.1. eliminate if no daily stats
6.3.2. eliminate if avg move time too long per config
6.3.3. eliminate if score rate too high or low per config
6.3.4. get timeout percentage in last 90 days

6.4. get candidate ongoing games
6.4.1. eliminate if too many ongoing games per config
6.4.2. eliminate if too few ongoing club match games per config
6.4.3. invite if no timeout and enough club match games

6.5. get candidate monthly archives, initialise counter, flag do not invite
for archive in archives, for game in games:
6.5.1. if game is more than 90 days ago, break
6.5.2. if game is not club match, continue
6.5.3. if game is timeout, break
6.5.4. increment counter, flag invite, break if counter meets config standard

6.6. if flag invite, invite
6.7. update candidate record

7. update local record
"""


@click.command()
@click.argument("club_name")
def recruitment(club_name: Optional[str] = None):
    configs = Configs.from_yaml()
    club_name = get_club_name(configs, club_name)
    membership(club_name)
    club = Club.from_str(configs.session, club_name)
