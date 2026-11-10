"""Render the public A/B portfolio as a static GitHub Pages site."""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

from flask import Flask

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import Config
from app.portfolio_studio import studio_bp
from app.views import bp as main_bp


OUTPUT = ROOT / "dist"


def create_render_app() -> Flask:
    app = Flask(
        "portfolio_export",
        template_folder=str(ROOT / "app" / "templates"),
        static_folder=str(ROOT / "app" / "static"),
    )
    app.config.from_object(Config)
    app.config["SERVER_NAME"] = "localhost"
    app.register_blueprint(main_bp)
    app.register_blueprint(studio_bp)
    return app


def make_page_relative(html: str, page: str) -> str:
    root_page = page == "/"
    asset_prefix = "" if root_page else "../../"
    html = html.replace('href="/static/', f'href="{asset_prefix}static/')
    html = html.replace('src="/static/', f'src="{asset_prefix}static/')

    if root_page:
        html = html.replace('href="/"', 'href="./"')
        html = html.replace('href="/experience/a"', 'href="experience/a/"')
        html = html.replace('href="/experience/b"', 'href="experience/b/"')
    else:
        html = html.replace('href="/"', 'href="../../"')
        html = html.replace('href="/experience/a"', 'href="../a/"')
        html = html.replace('href="/experience/b"', 'href="../b/"')

    # The editor and company-analysis workspace remain in the Flask app; this
    # public, static export contains only the A/B portfolio experiences.
    html = re.sub(
        r"\s*<a\b[^>]*href=\"/(?:studio|workspace)\"[^>]*>.*?</a>",
        "",
        html,
        flags=re.DOTALL,
    )
    if re.search(r'(?:href|src)="/(?:static|experience|studio|workspace)', html):
        raise RuntimeError(f"Unrewritten app URL in static page: {page or '/'}")
    return html


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = create_render_app()
    pages = {
        "/": OUTPUT / "index.html",
        "/experience/a": OUTPUT / "experience" / "a" / "index.html",
        "/experience/b": OUTPUT / "experience" / "b" / "index.html",
    }
    with app.test_client() as client:
        for route, target in pages.items():
            response = client.get(route)
            if response.status_code != 200:
                raise RuntimeError(f"Could not render {route}: HTTP {response.status_code}")
            target.parent.mkdir(parents=True, exist_ok=True)
            html = response.get_data(as_text=True)
            target.write_text(make_page_relative(html, route), encoding="utf-8")

    shutil.copytree(ROOT / "app" / "static", OUTPUT / "static", dirs_exist_ok=True)
    (OUTPUT / ".nojekyll").touch()
    print(f"Built {len(pages)} public portfolio pages in {OUTPUT}")


if __name__ == "__main__":
    main()
