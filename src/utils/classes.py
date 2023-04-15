from dataclasses import dataclass
import logging
from typing import Any
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_data(session: requests.Session, url: str):
    response = requests.get(url)


@dataclass
class Club:
    url_name: str
    name: str | None = None
    club_id: int | None = None
    admins: list[str] | None = None

    @property
    def api_profile(self):
        return f"https://api.chess.com/pub/club/{self.url_name}"

    @property
    def members(self):
        return f"https://api.chess.com/pub/club/{self.url_name}/members"

    def get_members(self, session: requests.Session):
        response = session.get(self.members)
        if response.status_code != 200:
            raise SystemExit(
                f"api call failed (status code {response.status_code})"
            )
        data: dict[str, list[dict[str, Any]]] = response.json()
        for group in data.values():
            for member in group:
                username: str = member["username"]
                joined: int = member["joined"]


@dataclass
class Player:
    username: str
    player_id: int | None = None

    @property
    def api_profile(self):
        return f"https://api.chess.com/pub/player/{self.username}"

    @property
    def api_stats(self):
        return f"https://api.chess.com/pub/player/{self.username}/stats"

    @property
    def api_clubs(self):
        return f"https://api.chess.com/pub/player/{self.username}/clubs"

    @property
    def api_games(self):
        return f"https://api.chess.com/pub/player/{self.username}/games"

    @property
    def api_archives(self):
        return (
            f"https://api.chess.com/pub/player/{self.username}/games/archives"
        )

    @property
    def api_matches(self):
        return f"https://api.chess.com/pub/player/{self.username}/matches"


@dataclass
class Member(Player):
    join_time: int | None = None
    is_closed: bool | None = None
    is_former: bool | None = None


@dataclass
class Candidate(Player):
    is_invited: bool = False
    has_joined: bool = False
    scanned_time: int | None = None
    club_count: int | None = None
    offline: int | None = None
    plays_daily: bool | None = None
    rating: int | None = None
    hrs_per_move: int | None = None
    score_rate: float | None = None


@dataclass
class Configs:
    email: str
    user_agent: str
    club_url: str
