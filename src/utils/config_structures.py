from typing import Self
import dataclass_wizard as dw
from dataclasses import dataclass, field
import requests

import yaml

from .dataclass_wizard_utils import remap


@dataclass
class _RecruitmentConfigs(dw.JSONWizard):
    avoid_admins: bool = True
    invited_expiry: int = 180
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
class _ClubConfig(dw.JSONWizard):
    recruitment: _RecruitmentConfigs


@dataclass
class Configs(dw.JSONWizard):
    email: str = ""
    username: str = ""
    default_club_name: str = field(metadata=remap("default_club"), default="")
    club_configs: dict[str, _ClubConfig] = field(
        metadata=remap("club_configs"), default_factory=dict
    )

    def __post_init__(self):
        if self.all_club_names and not self.default_club_name:
            self.default_club_name = self.all_club_names[0]

    @classmethod
    def from_yaml(cls) -> Self:
        with open("configs/configs.yml") as stream:
            # TODO: is this actually safe though?
            yml = yaml.safe_load(stream)
        return cls.from_dict(yml)

    @property
    def http_header(self) -> dict[str, str]:
        return {
            "User-Agent": f"email: {self.email}, username: {self.username}",
            "Accept": "application/json",
        }

    @property
    def session(self) -> requests.Session:
        session = requests.session()
        session.headers.update(self.http_header)
        return session

    @property
    def all_club_names(self) -> list[str]:
        return list(self.club_configs.keys())

    def get_club_configs(self, club_name: str) -> _ClubConfig:
        return self.club_configs[club_name]
