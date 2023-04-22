from typing import Optional
import click

from .structures import Club, Configs

from .membership import update_membership

from .functions import get_session


@click.group()
def cli():
    pass


@click.command()
@click.option("--club-name", "-c")
@click.option("--readonly", "-r", is_flag=True, default=True)
def membership(club_name: Optional[str] = None, readonly: bool = False):
    configs = Configs.get_configs(club_name)
    session = get_session(configs)
    club = Club.from_str(session, configs.club)
    update_membership(session, club, readonly)


cli.add_command(membership)


if __name__ == "__main__":
    cli()
