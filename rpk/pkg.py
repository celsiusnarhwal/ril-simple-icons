import contextlib
import json
import os
import shutil
import subprocess
import tarfile
import typing as t
from pathlib import Path
from tempfile import TemporaryDirectory

import casefy
import semver
import typer
from bs4 import BeautifulSoup
from halo import Halo
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
)
from rich.progress import track as Progress

from rpk import paths, utils

GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

app = typer.Typer(no_args_is_help=True, add_completion=False)


class Icon(BaseModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    slug: str
    title: str = ""
    svg_path: str = Field(None, alias="path")
    svg_circle: str = None


class SimpleIcon(Icon):
    hex: str

    @field_validator("slug")
    def validate_slug(cls, v):
        return "Si" + v.capitalize()


@app.command("simple")
def simple():
    pkg_dir = paths.packages() / "simple"
    src_dir = pkg_dir / "src"
    icons_dir = src_dir / "icons"

    shutil.rmtree(icons_dir, ignore_errors=True)
    icons_dir.mkdir(parents=True, exist_ok=True)

    requested_version = os.getenv("SIMPLE_ICONS_VERSION") or "latest"

    sorted_versions = sorted(
        [
            semver.Version.parse(v)
            for v in utils.get_package_info("simple-icons")["versions"]
        ],
        reverse=True,
    )

    if requested_version == "latest":
        version_to_use = sorted_versions[0]
    else:
        version_to_use = next(
            (
                v
                for v in sorted_versions
                if v.major <= int(requested_version) and not v.prerelease
            )
        )

    with TemporaryDirectory() as tmpdir:
        with contextlib.chdir(tmpdir):
            with Halo(f"Downloading Simple Icons {version_to_use}...") as spinner:
                subprocess.run(
                    [
                        "bun",
                        "add",
                        "--force",
                        "--no-save",
                        f"simple-icons@{version_to_use}",
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                spinner.succeed(f"Downloaded Simple Icons {version_to_use}")

            icons_json = json.loads(
                subprocess.check_output(
                    [
                        "node",
                        "-e",
                        "import * as icons from 'simple-icons'; console.log(JSON.stringify(icons))",
                    ]
                )
            )

            icons = TypeAdapter(list[SimpleIcon]).validate_python(icons_json.values())

        for icon in Progress(
            icons, description="Generating @celsiusnarhwal/ril-simple-icons..."
        ):
            icon_tsx = utils.render_template("icon.tsx.jinja", icon=icon, si_mode=True)

            tsx_file = icons_dir / f"{icon.slug}.tsx"
            tsx_file.write_text(icon_tsx)

        utils.render_index(src_dir, icons_dir, si_mode=True)
        utils.set_package_version(pkg_dir / "package.json", str(version_to_use))


@app.command("bootstrap")
def bootstrap():
    package_dir = paths.packages() / "bootstrap"
    src_dir = package_dir / "src"
    icons_dir = src_dir / "icons"

    shutil.rmtree(icons_dir, ignore_errors=True)
    icons_dir.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory() as tmpdir:
        with contextlib.chdir(tmpdir):
            with Halo("Downloading bootstrap-icons...") as spinner:
                subprocess.run(
                    ["npm", "pack", "bootstrap-icons"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                spinner.succeed("Downloaded bootstrap-icons")

            pkg = tarfile.open(next(Path.cwd().glob("*.tgz")))

    for file in Progress(
        pkg.getmembers(),
        description="Generating @celsiusnarhwal/ril-bootstrap-icons...",
    ):
        upstream_path = Path(file.path)

        if upstream_path.parts[:2] != ("package", "icons"):
            continue

        svg = BeautifulSoup(pkg.extractfile(file).read(), "html.parser")

        try:
            # noinspection PyArgumentList
            icon = Icon(
                slug="Bootstrap" + casefy.pascalcase(upstream_path.stem),
                svg_path=svg.find("path").attrs["d"],
            )
        except AttributeError:
            icon = Icon(
                slug="Bootstrap" + casefy.pascalcase(upstream_path.stem),
                svg_circle=str(svg.find("circle")),
            )

        icon_tsx = utils.render_template("icon.tsx.jinja", icon=icon)

        tsx_file = icons_dir.joinpath(icon.slug).with_suffix(".tsx")
        tsx_file.write_text(icon_tsx)

        utils.render_index(src_dir, icons_dir)
        utils.set_package_version(package_dir / "package.json")


@app.command("material")
def material(weight: t.Annotated[int, typer.Argument(show_default=False)]):
    package_dir = paths.packages() / "material"
    src_dir = package_dir / str(weight) / "src"
    icons_dir = src_dir / "icons"

    shutil.rmtree(icons_dir, ignore_errors=True)
    icons_dir.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory() as tmpdir:
        with contextlib.chdir(tmpdir):
            with Halo(f"Downloading @material-symbols/svg-{weight}...") as spinner:
                subprocess.run(
                    ["npm", "pack", f"@material-symbols/svg-{weight}"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                spinner.succeed(f"Downloaded @material-symbols/svg-{weight}")

            pkg = tarfile.open(next(Path.cwd().glob("*.tgz")))

    for file in Progress(
        pkg.getmembers(),
        description=f"Generating @celsiusnarhwal/ril-material-symbols-{weight}...",
    ):
        upstream_path = Path(file.path)

        if upstream_path.suffix != ".svg":
            continue

        downstream_path = Path(*upstream_path.parts[1:])

        downstream_path = downstream_path.with_suffix(".tsx").with_stem(
            "Material"
            + casefy.pascalcase(downstream_path.stem.replace("-fill", "")).title()
        )

        if upstream_path.stem.endswith("-fill"):
            downstream_path = Path(
                downstream_path.parent, "filled", downstream_path.name
            )

        svg_path = (
            BeautifulSoup(pkg.extractfile(file).read(), "html.parser")
            .find("path")
            .attrs["d"]
        )

        # noinspection PyArgumentList
        icon = Icon(slug=downstream_path.stem, svg_path=svg_path)
        icon_tsx = utils.render_template("icon.tsx.jinja", icon=icon)

        tsx_file = icons_dir / downstream_path
        tsx_file.parent.mkdir(parents=True, exist_ok=True)
        tsx_file.write_text(icon_tsx)

    for style in ["outlined", "rounded", "sharp"]:
        for substyle in [style, f"{style}/filled"]:
            utils.render_index(icons_dir / substyle, icons_dir / substyle)

    utils.set_package_version(package_dir / str(weight) / "package.json")
