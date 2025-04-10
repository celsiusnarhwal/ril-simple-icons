# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "hachitool",
#     "httpx",
#     "javascript",
#     "jinja2",
#     "pydantic",
#     "semver",
# ]
# ///

import json
import os
from pathlib import Path

import hachitool
import httpx
import javascript as js
import semver
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, TypeAdapter, field_validator


class Icon(BaseModel):
    title: str
    slug: str
    path: str
    hex: str

    @field_validator("slug")
    def validate_slug(cls, v):
        return "Si" + v.capitalize()


si_pkg_info = httpx.get("https://registry.npmjs.com/simple-icons").json()
version_to_use = None

for release in reversed(si_pkg_info["versions"]):
    version = semver.Version.parse(release)
    requested_version = os.getenv("SIMPLE_ICONS_VERSION")

    if not version.prerelease:
        if (
            requested_version and version.major <= int(requested_version)
        ) or not requested_version:
            version_to_use = str(version)
            hachitool.set_output("si-version", version_to_use)
            break


simple_icons = js.require("simple-icons", version=version_to_use)
icons_json = json.loads(js.eval_js("JSON.stringify(simple_icons)"))
icons = TypeAdapter(list[Icon]).validate_python(icons_json.values())

templates = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))
index_template = templates.get_template("index.ts.jinja")
icon_template = templates.get_template("icon.tsx.jinja")

Path("src/index.ts").write_text(index_template.render(icons=icons))

for icon in icons:
    rendered = icon_template.render(icon=icon)

    tsx = Path(f"src/icons/{icon.slug}.tsx")
    tsx.parent.mkdir(parents=True, exist_ok=True)
    tsx.write_text(rendered)
