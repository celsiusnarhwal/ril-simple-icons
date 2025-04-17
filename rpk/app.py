
import typer

import rpk.base
import rpk.pkg

app = typer.Typer(no_args_is_help=True, add_completion=False)

generator_app = typer.Typer(no_args_is_help=True, add_completion=False)
generator_app.add_typer(rpk.pkg.app, name="pkg")
generator_app.add_typer(rpk.base.app, name="base")

for name in ["generator", "gen", "g"]:
    app.add_typer(generator_app, name=name, hidden=name != "generator")

if __name__ == "__main__":
    app()
