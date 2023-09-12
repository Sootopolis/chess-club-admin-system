from typing import Optional
from sqlalchemy import TIMESTAMP, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column

from .alchemy_enums import CandidateStatus, GameResult, MatchStatus


class Base(DeclarativeBase, MappedAsDataclass):
    metadata = MetaData("the_great_british_empire")


class MemberORM(Base):
    __tablename__ = "member"
    player_id: Mapped[int] = mapped_column(primary_key=True)
    # username should be unique. however, i need to consider the possibility that someone changes
    # their username and someone else adopts their old name, in which case the order in which i
    # update the rows will be important. this won't happen very often but just in case.
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    joined: Mapped[int] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)


class MemberStatsORM(MemberORM):
    wins: Mapped[int] = mapped_column(default=0)
    draws: Mapped[int] = mapped_column(default=0)
    losses: Mapped[int] = mapped_column(default=0)


class CandidateORM(Base):
    __tablename__ = "candidate"
    player_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    scanned: Mapped[int] = mapped_column(TIMESTAMP, nullable=False)
    status: Mapped[CandidateStatus] = mapped_column(nullable=False)


class ClubORM(Base):
    __tablename__ = "club"
    club_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    url_name: Mapped[str] = mapped_column(nullable=False)


class DailyMatchORM(Base):
    __tablename__ = "daily_match"
    match_id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    status: Mapped[MatchStatus] = mapped_column(nullable=False)
    start_time: Mapped[int] = mapped_column(TIMESTAMP, nullable=True)
    end_time: Mapped[int] = mapped_column(TIMESTAMP, nullable=True)


class DailyBoardORM(Base):
    __tablename__ = "daily_board"
    match_id: Mapped[int] = mapped_column(primary_key=True)
    board_number: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(nullable=False)
    start_time: Mapped[Optional[int]] = mapped_column(TIMESTAMP, nullable=True)
    end_time: Mapped[Optional[int]] = mapped_column(TIMESTAMP, nullable=True)
    url_white: Mapped[Optional[str]] = mapped_column(nullable=True)
    url_black: Mapped[Optional[str]] = mapped_column(nullable=True)
    result_white: Mapped[Optional[GameResult]] = mapped_column(nullable=True)
    result_black: Mapped[Optional[GameResult]] = mapped_column(nullable=True)


wallace = MemberORM(0, "wallace", 0, True)
wallace_stats = MemberStatsORM(0, "wallace", 0, True)
maurizzio = CandidateORM(1, "maurizzio", 1, CandidateStatus.INVITED)

print(wallace)
print(wallace_stats)
print(maurizzio)
