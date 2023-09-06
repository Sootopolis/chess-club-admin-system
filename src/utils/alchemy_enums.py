from enum import StrEnum, auto


class CandidateStatus(StrEnum):
    JOINED = auto()
    INVITED = auto()
    TIMEOUT = auto()
    CHECKED = auto()


class MatchStatus(StrEnum):
    FINISHED = auto()
    IN_PROGRESS = auto()
    REGISTERED = auto()
