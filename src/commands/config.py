import click

from ..utils.functions import validate_email
from ..utils.structures import Configs


@click.command()
@click.option("--hard", is_flag=True)
def setup(hard: bool = False):
    configs = Configs.from_yaml()
    if hard:
        confirmation = input('enter "HARD RESET CONFIGS" to reset all configs')
        if confirmation == "HARD RESET CONFIGS":
            configs = Configs()
        else:
            raise SystemExit("confirmation failed")
    email = input("enter email address for http header: ")
    while not validate_email(email):
        email = input("please enter a valid email address: ")
    username = input("enter chess.com username for http header: ")
    configs.email = email
    configs.username = username


# TODO: finish the rest of it. but honestly i don't give a fuck.


@click.group()
def config():
    pass


config.add_command(setup)
