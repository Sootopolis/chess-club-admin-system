from dataclasses import dataclass, field
import dataclass_wizard as dw
import requests
from typing import Optional
import yaml


# helper functions


def _remap(*keys: str) -> dict[str, dw.models.JSON]:
    """returns remapping information for field metadata.
    `keys` are possible names you want mapped into the attribute.
    by default, camel cases are mapped into snake cases."""

    return {"__remapping__": dw.json_key(*keys)}


def _get_data(session: requests.Session, url: str, timeout: int = 5):
    """gets data from the chess.com public api using url"""

    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return data


# data structures


@dataclass
class _PlayerGameTypeLast(dw.JSONWizard):
    rating: int


@dataclass
class _PlayerGameTypeRecord(dw.JSONWizard):
    wins: int = field(metadata=_remap("win"))
    draws: int = field(metadata=_remap("draw"))
    losses: int = field(metadata=_remap("loss"))
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
    player_id: Optional[int] = None

    @property
    def api(self) -> str:
        return f"https://api.chess.com/pub/player/{self.username}"

    def update_player_id(self, session: requests.Session) -> None:
        if self.player_id is None:
            data = _get_data(session, self.api)
            self.player_id = Member.from_dict(data).player_id

    @property
    def url(self) -> str:
        return f"https://www.chess.com/player/{self.username}"

    @property
    def api_clubs(self) -> str:
        return f"{self.api}/clubs"

    def get_club_urls(self, session: requests.Session) -> list[str]:
        data: dict[str, list[dict[str, str]]] = _get_data(
            session, self.api_clubs
        )
        return [club["url"] for club in data["clubs"]]

    @property
    def api_stats(self) -> str:
        return f"{self.api}/stats"

    def get_stats(self, session: requests.Session) -> _PlayerStats:
        return _PlayerStats.from_dict(_get_data(session, self.api_stats))

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
    def all(self) -> set["Member"]:
        return set(self.weekly + self.monthly + self.all_time)


@dataclass
class _ClubMatch(dw.JSONWizard):
    api: str = field(metadata=_remap("@id"))
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
    api: str = field(metadata=_remap("@id"))
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
    api: str = field(metadata=_remap("@id"))
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

    @staticmethod
    def from_str(session: requests.Session, s: str):
        """gets `Board` object from api url"""
        return Board.from_dict(_get_data(session, s))


@dataclass
class Match(dw.JSONWizard):
    """object that represents a match, initialise with `from_str()`"""

    api: str = field(metadata=_remap("@id"))
    name: str
    url: str
    status: str
    boards: int
    settings: _MatchSettings
    teams: _MatchTeams
    start_time: Optional[int] = None
    end_time: Optional[int] = None

    @staticmethod
    def from_str(session: requests.Session, s: str):
        """gets `Match` object with api url"""
        return Match.from_dict(_get_data(session, s))


@dataclass
class Candidate(_Player):
    pass


@dataclass
class Member(_Player):
    joined: Optional[int] = None
    is_active: bool = field(default=True)

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, Member):
            raise TypeError("cannot compare `_ClubMember` and something else")
        # not using `is not None` for backwards compatibility!
        if self.joined and __value.joined and self.joined != __value.joined:
            return False
        if (
            self.player_id
            and __value.player_id
            and self.player_id != __value.player_id
        ):
            return False
        return self.username == __value.username

    def __lt__(self, __value: object) -> bool:
        if not isinstance(__value, Member):
            raise TypeError("comparing a `Member` object to something else")
        return self.username < __value.username

    def __gt__(self, __value: object) -> bool:
        if not isinstance(__value, Member):
            raise TypeError("comparing a `Member` object to something else")
        return self.username > __value.username

    def __hash__(self) -> int:
        return hash(self.username)


@dataclass
class MemberWithStats(Member):
    wins: Optional[int] = field(default=None, compare=False)
    draws: Optional[int] = field(default=None, compare=False)
    losses: Optional[int] = field(default=None, compare=False)


@dataclass
class Club(dw.JSONWizard):
    """object that represents a club, initialise with `from_str()`"""

    api: str = field(metadata=_remap("@id"))
    name: Optional[str] = None
    club_id: Optional[int] = None
    admins: list[str] = field(default_factory=list, metadata=_remap("admin"))

    @property
    def url_name(self) -> str:
        return self.api.split("/")[-1]

    @property
    def url(self) -> str:
        return f"https://www.chess.com/club/{self.url_name}"

    @property
    def api_members(self) -> str:
        return f"{self.api}/members"

    def get_members(self, session: requests.Session) -> set[Member]:
        """returns list of club members"""
        data = _get_data(session, self.api_members)
        return _ClubMembers.from_dict(data).all

    @property
    def api_matches(self) -> str:
        return f"{self.api}/matches"

    def get_matches(self, session: requests.Session) -> _ClubMatches:
        """returns matches of the club as `ClubMatches` object"""
        return _ClubMatches.from_dict(_get_data(session, self.api_matches))

    @staticmethod
    def from_str(session: requests.Session, s: str) -> "Club":
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
        return Club.from_dict(_get_data(session, api))


# data structures for user configurations


@dataclass
class _RecruitmentConfigs(dw.JSONWizard):
    avoid_admins: bool = True
    timeout_expiry: int = 90
    checked_expiry: int = 30
    min_elo: int = 1000
    max_elo: int = 2000
    min_score_rate: float = 0.45
    max_score_rate: float = 0.85
    min_matches_played: int = 10
    min_matches_ongoing: int = 1
    max_games_ongoing: int = 100
    max_clubs: int = 35
    max_hrs_per_move: int = 18
    max_hrs_offline: int = 48


@dataclass
class Configs(dw.JSONWizard):
    email: str
    username: str
    club: str
    recruitment: _RecruitmentConfigs

    @staticmethod
    def get_configs(club: Optional[str] = None):
        with open("configs/configs.yml") as stream:
            yml = yaml.safe_load(stream)
        configs = _AllClubConfigs.from_dict(yml)
        if club is None:
            return configs.club_configs[configs.default_club]
        else:
            return configs.club_configs[club]

    @property
    def http_header(self):
        return {
            "User-Agent": self.username,
            "From": self.email,
            "Accept": "application/json",
        }


@dataclass
class _AllClubConfigs(dw.JSONWizard):
    default_club: str
    club_configs: dict[str, Configs]


# data structures for local handling


@dataclass
class ExistingMembers:
    current: set[Member] = field(default_factory=set, init=False)
    archive: set[Member] = field(default_factory=set, init=False)


@dataclass
class MembershipChanges:
    left: list[Member] = field(default_factory=list, init=False)
    joined: list[Member] = field(default_factory=list, init=False)
    closed: list[Member] = field(default_factory=list, init=False)
    reopened: list[Member] = field(default_factory=list, init=False)
    returned: list[Member] = field(default_factory=list, init=False)
    renamed: list[tuple[Member, Member]] = field(
        default_factory=list, init=False
    )
    renamed_gone: list[Member] = field(default_factory=list, init=False)
    renamed_returned: list[tuple[Member, Member]] = field(
        default_factory=list, init=False
    )

    @staticmethod
    def __print_member(title: str, member_list: list[Member]) -> None:
        if member_list:
            print(title)
            for member in member_list:
                print(member.username, member.url)

    @staticmethod
    def __print_renamed(
        title: str, member_list: list[tuple[Member, Member]]
    ) -> None:
        if member_list:
            print(title)
            for member_old, member_new in member_list:
                print(
                    member_old.username,
                    "->",
                    member_new.username,
                    member_new.url,
                )

    def __print_changes(self) -> None:
        self.__print_member("goners:", self.left)
        self.__print_member("newbies:", self.joined)
        self.__print_member("closed:", self.closed)
        self.__print_member("reopened:", self.reopened)
        self.__print_member("returned:", self.returned)
        self.__print_renamed("renamed:", self.renamed)
        self.__print_member("renamed and gone:", self.renamed_gone)
        self.__print_renamed("renamed and returned:", self.renamed_returned)

    def summarise(self, existing: ExistingMembers) -> None:
        self.__print_changes()
        for member in self.left:
            member.is_active = False
            existing.archive.add(member)
            existing.current.remove(member)
        for member in self.joined:
            existing.current.add(member)
        for member in self.closed:
            member.is_active = False
        for member in self.reopened:
            member.is_active = True
        for member_old, member_new in self.renamed:
            member_old.username = member_new.username
        for member in self.renamed_gone:
            member.is_active = False
        for member_old, member_new in self.renamed_returned:
            member_old.username = member_new.username
            member_old.is_active = True
        print(f"total: {len(existing.current)}")
