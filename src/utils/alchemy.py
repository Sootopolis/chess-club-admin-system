from enum import StrEnum, auto

from sqlalchemy import TIMESTAMP, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column


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


class CandidateStatus(StrEnum):
    JOINED = auto()
    INVITED = auto()
    TIMEOUT = auto()
    CHECKED = auto()


class CandidateORM(Base):
    __tablename__ = "candidate"
    player_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    scanned: Mapped[int] = mapped_column(TIMESTAMP, nullable=False)
    status: Mapped[CandidateStatus] = mapped_column(nullable=False)


wallace = MemberORM(0, "wallace", 0, True)
wallace_stats = MemberStatsORM(0, "wallace", 0, True)
maurizzio = CandidateORM(1, "maurizzio", 1, CandidateStatus.INVITED)

print(wallace)
print(wallace_stats)
print(maurizzio)
