import typer

from .vsbk import vsbk

app = typer.Typer(help="VSBuildKit CLI")
app.command()(vsbk)

if __name__ == "__main__":
    app()
