from dataclasses import dataclass, field
import dataclass_wizard as dw
import requests
from typing import Optional


def remap(*keys: str) -> dict[str, dw.models.JSON]:
    """returns remapping information for field metadata.
    `keys` are possible names you want mapped into the attribute.
    by default, camel cases are mapped into snake cases."""

    return {"__remapping__": dw.json_key(*keys)}


def get_data(session: requests.Session, url: str, timeout: int = 5):
    """gets data from the chess.com public api using url"""

    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as error:
        raise SystemExit(f"http request failed for this url:\n{url}\n{error}")


@dataclass
class __PlayerGameTypeLast(dw.JSONWizard):
    rating: int


@dataclass
class __PlayerGameTypeRecord(dw.JSONWizard):
    wins: int = field(metadata=remap("win"))
    draws: int = field(metadata=remap("draw"))
    losses: int = field(metadata=remap("loss"))
    time_per_move: int
    timeout_percent: float

    @property
    def score_rate(self) -> float:
        return self.wins + self.draws / 2


@dataclass
class __PlayerGameTypeStats(dw.JSONWizard):
    last: __PlayerGameTypeLast
    record: __PlayerGameTypeRecord


@dataclass
class __PlayerStats(dw.JSONWizard):
    chess_daily: Optional[__PlayerGameTypeStats] = None
    chess960_daily: Optional[__PlayerGameTypeStats] = None


@dataclass
class __ClubMembers(dw.JSONWizard):
    weekly: list["Member"]
    monthly: list["Member"]
    all_time: list["Member"]

    @property
    def all(self):
        return self.weekly + self.monthly + self.all_time


@dataclass
class __ClubMatch(dw.JSONWizard):
    api: str = field(metadata=remap("@id"))
    name: str
    opponent: str
    time_class: str
    start_time: Optional[int] = None
    result: Optional[str] = None


@dataclass
class __ClubMatches(dw.JSONWizard):
    finished: list[__ClubMatch]
    in_progress: list[__ClubMatch]
    registered: list[__ClubMatch]


@dataclass
class __MatchSettings(dw.JSONWizard):
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
class __MatchPlayer(dw.JSONWizard):
    username: str
    board: str
    played_as_white: Optional[str] = None
    played_as_black: Optional[str] = None


@dataclass
class __MatchTeam(dw.JSONWizard):
    api: str = field(metadata=remap("@id"))
    name: str
    score: int
    players: list[__MatchPlayer]
    fair_play_removals: list[str] = []


@dataclass
class __MatchTeams(dw.JSONWizard):
    team1: __MatchTeam
    team2: __MatchTeam


@dataclass
class __GamePlayer(dw.JSONWizard):
    api: str = field(metadata=remap("@id"))
    username: str
    result: str


@dataclass
class __Game(dw.JSONWizard):
    url: str
    match: str
    white: __GamePlayer
    black: __GamePlayer
    start_time: int
    end_time: Optional[int]


@dataclass
class Board(dw.JSONWizard):
    """class that represents boards, initialise with `from_str()`"""

    board_scores: dict[str, int]
    games: list[__Game]

    @staticmethod
    def from_str(session: requests.Session, s: str):
        """gets `Board` object from api url"""
        return Board.from_dict(get_data(session, s))


@dataclass
class Match(dw.JSONWizard):
    """object that represents a match, initialise with `from_str()`"""

    api: str = field(metadata=remap("@id"))
    name: str
    url: str
    status: str
    boards: int
    settings: __MatchSettings
    teams: __MatchTeams
    start_time: Optional[int] = None
    end_time: Optional[int] = None

    @staticmethod
    def from_str(session: requests.Session, s: str):
        """gets `Match` object with api url"""
        return Match.from_dict(get_data(session, s))


@dataclass
class Player(dw.JSONWizard):
    username: str
    player_id: Optional[str] = None

    @property
    def api(self):
        return f"https://api.chess.com/pub/club/{self.username}"

    @property
    def api_clubs(self):
        return f"{self.api}/clubs"

    def get_club_count(self, session: requests.Session) -> int:
        data: dict[str, list] = get_data(session, self.api_clubs)
        return len(data["clubs"])

    @property
    def api_stats(self):
        return f"{self.api}/stats"

    def get_stats(self, session: requests.Session):
        return __PlayerStats.from_dict(get_data(session, self.api_stats))

    @property
    def api_matches(self):
        return f"{self.api}/matches"

    @property
    def api_games(self):
        return f"{self.api}/games"

    def get_api_archive(self, year: int, month: int):
        return f"{self.api}/games/archive/{year}/{month}"


@dataclass
class Candidate(Player):
    pass


@dataclass
class Member(Player):
    joined: Optional[int] = None
    is_closed: Optional[bool] = None
    is_former: Optional[bool] = None
    wins: Optional[int] = None
    draws: Optional[int] = None
    losses: Optional[int] = None


@dataclass
class Club(dw.JSONWizard):
    """object that represents a club, initialise with `from_str()`"""

    api: str
    name: Optional[str] = None
    club_id: Optional[int] = None
    admins: Optional[list[str]] = field(default=None, metadata=remap("admin"))

    @property
    def api_members(self):
        return f"{self.api}/members"

    def get_members(self, session: requests.Session) -> list[Member]:
        """returns list of club members"""
        data = get_data(session, self.api_members)
        return __ClubMembers.from_dict(data).all

    @property
    def api_matches(self):
        return f"{self.api}/matches"

    def get_matches(self, session: requests.Session) -> __ClubMatches:
        """returns matches of the club as `ClubMatches` object"""
        return __ClubMatches.from_dict(get_data(session, self.api_matches))

    @staticmethod
    def from_str(session: requests.Session, s: str):
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
        return Club.from_dict(get_data(session, s))


session = requests.session()
session.headers.update({"From": "yuzhuo.w@gmail.com"})
club = Club.from_str(session, "tgbe-office-for-planning-and-preparation")
print(club)
