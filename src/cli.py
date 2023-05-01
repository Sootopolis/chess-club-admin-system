import click

from .commands.membership import membership
from .commands.recruitment import recruitment


@click.group()
def cli():
    pass


cli.add_command(membership)
cli.add_command(recruitment)

if __name__ == "__main__":
    cli()
