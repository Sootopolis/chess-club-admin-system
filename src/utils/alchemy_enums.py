from enum import Enum, StrEnum, auto


class CandidateStatus(Enum):
    JOINED = auto()
    INVITED = auto()
    TIMEOUT = auto()
    CHECKED = auto()


class MatchStatus(StrEnum):
    FINISHED = auto()
    IN_PROGRESS = auto()
    REGISTRATION = auto()


class GameResultCategory(float, Enum):
    WIN = 1.0
    DRAW = 0.5
    LOSS = 0.0


class GameResult(Enum):
    WIN = "win"
    CHECKMATE = "checkmated"
    AGREEMENT = "agreed"
    REPETITION = "repetition"
    TIMEOUT = "timeout"
    RESIGNATION = "resigned"
    STALEMATE = "stalemate"
    LOSS = "lose"
    INSUFFICIENT = "insufficient"
    FIFTY_MOVE = "50move"
    TIMEOUT_INSUFFICIENT = "timevsinsufficient"
    DRAW = "draw"


results: dict[GameResult, GameResultCategory] = {
    GameResult.WIN: GameResultCategory.WIN,
    GameResult.DRAW: GameResultCategory.DRAW,
    GameResult.AGREEMENT: GameResultCategory.DRAW,
    GameResult.REPETITION: GameResultCategory.DRAW,
    GameResult.STALEMATE: GameResultCategory.DRAW,
    GameResult.INSUFFICIENT: GameResultCategory.DRAW,
    GameResult.FIFTY_MOVE: GameResultCategory.DRAW,
    GameResult.TIMEOUT_INSUFFICIENT: GameResultCategory.DRAW,
    GameResult.LOSS: GameResultCategory.LOSS,
    GameResult.CHECKMATE: GameResultCategory.LOSS,
    GameResult.TIMEOUT: GameResultCategory.LOSS,
    GameResult.RESIGNATION: GameResultCategory.LOSS,
}
