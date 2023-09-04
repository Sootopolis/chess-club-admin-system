from dataclasses import dataclass, field
from typing import Iterable, Optional, Self

import dataclass_wizard as dw
import requests

from .dataclass_wizard_utils import get_data, remap

# data structures


@dataclass
class _PlayerGameTypeLast(dw.JSONWizard):
    rating: int


@dataclass
class _PlayerGameTypeRecord(dw.JSONWizard):
    wins: int = field(metadata=remap("win"))
    draws: int = field(metadata=remap("draw"))
    losses: int = field(metadata=remap("loss"))
    time_per_move: int
    timeout_percent: float

    @property
    def score_rate(self) -> float:
        return self.wins + self.draws / 2


@dataclass
class _PlayerGameTypeStats(dw.JSONWizard):
    last: _PlayerGameTypeLast
    record: _PlayerGameTypeRecord


@dataclass
class _PlayerStats(dw.JSONWizard):
    chess_daily: Optional[_PlayerGameTypeStats] = None
    chess960_daily: Optional[_PlayerGameTypeStats] = None


@dataclass
class _Player(dw.JSONWizard):
    username: str
    player_id: Optional[int] = field(default=None, metadata=remap("player_id"))

    @property
    def api(self) -> str:
        return f"https://api.chess.com/pub/player/{self.username}"

    def update_player_id(self, session: requests.Session) -> None:
        if self.player_id is None:
            data = get_data(session, self.api)
            self.player_id = Member.from_dict(data).player_id

    @property
    def url(self) -> str:
        return f"https://www.chess.com/member/{self.username}"

    @property
    def api_clubs(self) -> str:
        return f"{self.api}/clubs"

    def get_club_urls(self, session: requests.Session) -> list[str]:
        data: dict[str, list[dict[str, str]]] = get_data(session, self.api_clubs)
        return [club["url"] for club in data["clubs"]]

    @property
    def api_stats(self) -> str:
        return f"{self.api}/stats"

    def get_stats(self, session: requests.Session) -> _PlayerStats:
        return _PlayerStats.from_dict(get_data(session, self.api_stats))

    @property
    def api_matches(self) -> str:
        return f"{self.api}/matches"

    @property
    def api_games(self) -> str:
        return f"{self.api}/games"

    def api_archive(self, year: int, month: int) -> str:
        return f"{self.api}/games/archive/{year}/{month}"


@dataclass
class _ClubMembers(dw.JSONWizard):
    weekly: list["Member"]
    monthly: list["Member"]
    all_time: list["Member"]

    @property
    def all(self) -> list["Member"]:
        return self.weekly + self.monthly + self.all_time


@dataclass
class _ClubMatch(dw.JSONWizard):
    api: str = field(metadata=remap("@id"))
    name: str
    opponent: str
    time_class: str
    start_time: Optional[int] = None
    result: Optional[str] = None


@dataclass
class _ClubMatches(dw.JSONWizard):
    finished: list[_ClubMatch]
    in_progress: list[_ClubMatch]
    registered: list[_ClubMatch]


@dataclass
class _MatchSettings(dw.JSONWizard):
    rules: str
    time_class: str
    time_control: str
    autostart: bool
    initial_setup: Optional[str] = None
    min_team_players: Optional[int] = None
    max_team_players: Optional[int] = None
    min_required_games: Optional[int] = None
    initial_group_size: Optional[int] = None
    min_rating: Optional[int] = None
    max_rating: Optional[int] = None


@dataclass
class _MatchPlayer(dw.JSONWizard):
    username: str
    board: str
    played_as_white: Optional[str] = None
    played_as_black: Optional[str] = None


@dataclass
class _MatchTeam(dw.JSONWizard):
    api: str = field(metadata=remap("@id"))
    name: str
    score: int
    players: list[_MatchPlayer]
    fair_play_removals: list[str] = field(default_factory=list)


@dataclass
class _MatchTeams(dw.JSONWizard):
    team1: _MatchTeam
    team2: _MatchTeam


@dataclass
class _GamePlayer(dw.JSONWizard):
    api: str = field(metadata=remap("@id"))
    username: str
    result: str


@dataclass
class _Game(dw.JSONWizard):
    url: str
    match: str
    white: _GamePlayer
    black: _GamePlayer
    start_time: int
    end_time: Optional[int]


@dataclass
class Board(dw.JSONWizard):
    """class that represents boards, initialise with `from_str()`"""

    board_scores: dict[str, int]
    games: list[_Game]

    @classmethod
    def from_str(cls, session: requests.Session, s: str) -> Self:
        """gets `Board` object from api url"""
        return cls.from_dict(get_data(session, s))


@dataclass
class Match(dw.JSONWizard):
    """object that represents a match, initialise with `from_str()`"""

    api: str = field(metadata=remap("@id"))
    name: str
    url: str
    status: str
    boards: int
    settings: _MatchSettings
    teams: _MatchTeams
    start_time: Optional[int] = None
    end_time: Optional[int] = None

    @classmethod
    def from_str(cls, session: requests.Session, s: str) -> Self:
        """gets `Match` object with api url"""
        return cls.from_dict(get_data(session, s))


@dataclass
class Member(_Player):
    joined: Optional[int] = None
    is_active: bool = field(default=True, metadata=remap("is_active"))

    def __lt__(self, __value: object) -> bool:
        if not isinstance(__value, _Player):
            raise TypeError("cannot compare a `Member` with non `_Player`")
        return self.username < __value.username

    def __gt__(self, __value: object) -> bool:
        if not isinstance(__value, _Player):
            raise TypeError("cannot compare a `Member` with non `_Player`")
        return self.username > __value.username


@dataclass
class MemberWithStats(Member):
    wins: Optional[int] = field(default=None, compare=False)
    draws: Optional[int] = field(default=None, compare=False)
    losses: Optional[int] = field(default=None, compare=False)


@dataclass
class Club(dw.JSONWizard):
    """object that represents a club, initialise with `from_str()`"""

    api: str = field(metadata=remap("@id"))
    name: Optional[str] = None
    club_id: Optional[int] = None
    admins: list[str] = field(default_factory=list, metadata=remap("admin"))

    @property
    def url_name(self) -> str:
        return self.api.split("/")[-1]

    @property
    def url(self) -> str:
        return f"https://www.chess.com/club/{self.url_name}"

    @property
    def api_members(self) -> str:
        return f"{self.api}/members"

    def get_members(self, session: requests.Session) -> list[Member]:
        """returns list of club members"""
        data = get_data(session, self.api_members)
        return _ClubMembers.from_dict(data).all

    @property
    def api_matches(self) -> str:
        return f"{self.api}/matches"

    def get_matches(self, session: requests.Session) -> _ClubMatches:
        """returns matches of the club as `ClubMatches` object"""
        return _ClubMatches.from_dict(get_data(session, self.api_matches))

    @classmethod
    def from_str(cls, session: requests.Session, s: str) -> Self:
        """gets `Club` object from:

        1. url
            * https://api.chess.com/pub/club/team-england
            * https://www.chess.com/club/team-england

        2. last part of url
            * team-england

        3. space separated string (use with caution!)
            * team england
        """

        s = "-".join(s.strip(" /").split("/")[-1].split())
        api = f"https://api.chess.com/pub/club/{s}"
        return cls.from_dict(get_data(session, api))


# data structures for local handling


class MemberRecords:
    def __init__(self, members: Optional[Iterable[Member]]) -> None:
        self.current: dict[int, Member] = {}
        self.archive: dict[int, Member] = {}
        if members:
            for member in members:
                assert member.player_id
                if member.is_active:
                    self.current[member.player_id] = member
                else:
                    self.archive[member.player_id] = member

    def update(self, members: Iterable[Member], is_active: bool) -> None:
        if is_active:
            src_dict, dst_dict = self.archive, self.current
        else:
            src_dict, dst_dict = self.current, self.archive
        for member in members:
            assert member.player_id
            member.is_active = is_active
            if member.player_id in src_dict:
                del src_dict[member.player_id]
            dst_dict[member.player_id] = member

    @property
    def all(self) -> list[Member]:
        return sorted(self.current.values()) + sorted(self.archive.values())
