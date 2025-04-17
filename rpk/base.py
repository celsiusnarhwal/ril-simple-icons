import json
import shutil
import typing as t

import typer
from merge_args import merge_args

from rpk import paths, utils

app = typer.Typer(no_args_is_help=True, add_completion=False)


def shared_args(func: t.Callable):
    # noinpsection PyUnusedLocal
    @merge_args(func)
    def wrapper(
        ctx: typer.Context,
        remove: t.Annotated[bool, typer.Option("--remove")] = False,
        **kwargs,
    ):
        return func(ctx=ctx, **kwargs)

    return wrapper


@app.command("simple")
@shared_args
def simple(ctx: typer.Context):
    pkg_dir = paths.packages() / "simple"

    if ctx.params["remove"]:
        shutil.rmtree(pkg_dir)
        return

    pkg_dir.mkdir(parents=True, exist_ok=True)
    utils.extend_tsconfig(pkg_dir)

    package_json = utils.base_package_json()
    package_json["name"] = "@celsiusnarhwal/ril-simple-icons"
    package_json["scripts"]["generate"] = "rpk gen pkg simple"
    pkg_dir.joinpath("package.json").write_text(json.dumps(package_json, indent=2))


@app.command("bootstrap")
@shared_args
def bootstrap(ctx: typer.Context):
    pkg_dir = paths.packages() / "bootstrap"

    if ctx.params["remove"]:
        shutil.rmtree(pkg_dir)
        return

    pkg_dir.mkdir(parents=True, exist_ok=True)
    utils.extend_tsconfig(pkg_dir)

    package_json = utils.base_package_json()
    package_json["name"] = "@celsiusnarhwal/ril-bootstrap-icons"
    package_json["scripts"]["generate"] = "rpk gen pkg bootstrap"
    pkg_dir.joinpath("package.json").write_text(json.dumps(package_json, indent=2))


@app.command("material")
@shared_args
def material(ctx: typer.Context, weight: t.Annotated[int, typer.Argument(show_default=False)] = None):
    material_root = paths.packages() / "material"

    if ctx.params["remove"]:
        shutil.rmtree(material_root)
        return

    if weight:
        weights = [weight]
    else:
        weights = range(100, 800, 100)

    for weight in weights:
        pkg_dir = material_root / str(weight)
        pkg_dir.mkdir(parents=True, exist_ok=True)

        utils.extend_tsconfig(pkg_dir)

        package_json = utils.base_package_json()
        package_json["name"] = f"@celsiusnarhwal/ril-material-symbols-{weight}"
        package_json["scripts"]["generate"] = f"rpk gen pkg material {weight}"

        for style in ["outlined", "rounded", "sharp"]:
            for substyle in [style, f"{style}/filled"]:
                package_json.setdefault("exports", {}).setdefault(
                    "substyle", {}
                ).update(
                    {
                        "main": f"{substyle}/index.cjs",
                        "module": f"{substyle}/index.js",
                        "typings": f"{substyle}/index.d.ts",
                    }
                )

        for key in ["main", "module", "typings"]:
            package_json.pop(key, None)

        pkg_dir.joinpath("package.json").write_text(json.dumps(package_json, indent=2))


@app.command(name="all")
@shared_args
def generate_all(ctx: typer.Context):
    simple(ctx=ctx)
    bootstrap(ctx=ctx)
    material(ctx=ctx)
