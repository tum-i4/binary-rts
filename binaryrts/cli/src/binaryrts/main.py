import logging
import sys

import typer
from binaryrts.commands import select, convert, utils

logging.basicConfig(
    format="[%(process)d] %(asctime)s: %(filename)s - %(levelname)s: %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)

app = typer.Typer()
app.add_typer(select.app, name="select")
app.add_typer(convert.app, name="convert")
app.add_typer(utils.app, name="utils")


@app.callback()
def callback(debug: bool = False):
    """
    BinaryRTS CLI
    """
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
