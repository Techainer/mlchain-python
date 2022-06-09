from __future__ import print_function

import platform
import sys
import click
import flask
import starlette
from .init import init_command
from .run import run_command
from .artifact import artifact_command
from .serve import serve_command
from .. import __version__


def get_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return

    message = "Python %(python)s\nMlChain %(mlchain)s\nFlask %(flask)s\nStarlette %(starlette)s\n"
    click.echo(
        message
        % {
            "python": platform.python_version(),
            "mlchain": __version__,
            "flask": flask.__version__,
            "starlette": starlette.__version__
        },
        color=ctx.color,
    )
    ctx.exit()


def main(as_module=False, is_testing=False):
    version_option = click.Option(
        ["--version"],
        help="Show the mlchain version",
        expose_value=False,
        callback=get_version,
        is_flag=True,
        is_eager=True,
    )
    cli = click.Group(params=[version_option])
    cli.add_command(run_command)
    cli.add_command(init_command)
    cli.add_command(artifact_command)
    cli.add_command(serve_command)
    if is_testing:
        return cli
    cli.main(args=sys.argv[1:], prog_name="python -m mlchain" if as_module else None)  # pragma: no cover

if __name__ == "__main__":  # pragma: no cover
    cli = main(as_module=True)
