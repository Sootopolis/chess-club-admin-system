import click

from .membership import membership


@click.group()
def cli():
    pass


cli.add_command(membership)

if __name__ == "__main__":
    cli()
