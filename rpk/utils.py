import json
from pathlib import Path

import hishel
import httpx
import semver
from jinja2 import Environment, FileSystemLoader
from sortedcontainers import SortedList

from rpk import paths

templates = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))


def base_package_json():
    return {
        "license": "MIT",
        "author": "celsius narhwal",
        "repository": {
            "url": "https://github.com/celsiusnarhwal/ril-packages",
        },
        "main": "dist/index.cjs",
        "module": "dist/index.js",
        "typings": "dist/index.d.ts",
        "type": "module",
        "files": ["dist"],
        "scripts": {
            "build": "bun run generate && bun tsup",
            "publish": "bunx can-npm-publish && bun publish --access public",
        },
        "tsup": {
            "entry": ["src/**/index.ts"],
            "dts": True,
            "splitting": False,
            "sourcemap": True,
            "clean": True,
            "format": ["esm", "cjs"],
            "outDir": "dist",
            "external": ["react", "react/jsx-runtime"],
            "target": "esnext"
        },
        "peerDependencies": {"react": "^17"},
    }


def get_package_info(package_name: str):
    with hishel.CacheClient(base_url="https://registry.npmjs.org") as npm:
        resp = npm.get(package_name)
        resp.raise_for_status()
        return resp.json()


def get_template(name: str):
    return templates.get_template(name)


def render_template(name: str, **context):
    return get_template(name).render(**context)


def render_index(at: Path, using: Path, si_mode: bool = False):
    icons = SortedList(
        [
            {"slug": file.stem, "relative_path": file.relative_to(at).with_suffix("")}
            for file in using.glob("*.tsx")
        ],
        key=lambda x: x["slug"],
    )

    at.joinpath("index.ts").write_text(
        render_template("index.ts.jinja", icons=icons, si_mode=si_mode)
    )


def extend_tsconfig(to: Path, **config):
    tsconfig = {
        "extends": str(
            paths.root().joinpath("tsconfig.base.json").relative_to(to, walk_up=True)
        ),
        "include": ["src"],
        **config,
    }

    json.dump(tsconfig, to.joinpath("tsconfig.json").open("w"))


def set_package_version(package_json_file: Path, version: str = None):
    package_json = json.load(package_json_file.open())

    if version:
        package_json["version"] = version
    else:
        try:
            published_versions = sorted(get_package_info(package_json["name"])["versions"], key=semver.Version.parse)
        except httpx.HTTPStatusError:
            package_json["version"] = "1.0.0"
        else:
            package_json["version"] = str(semver.Version.parse(published_versions[-1]).bump_minor())

    json.dump(package_json, package_json_file.open("w"), indent=2)

