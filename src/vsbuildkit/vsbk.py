from typing_extensions import Annotated
import typer

def vsbk(
        config:  Annotated[str, typer.Option("--config-file", "-c", help="Path to the configuration file.")] = "",
):
    if config:
        print(f"Configuration file: {config}")
    else:
        print("No configuration file provided.")