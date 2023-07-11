import click

from .commands.config import config
from .commands.membership import membership
from .commands.recruitment import recruitment


@click.group()
def cli():
    pass


cli.add_command(membership)
cli.add_command(recruitment)
cli.add_command(config)

if __name__ == "__main__":
    cli()
