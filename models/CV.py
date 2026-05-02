from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
from typing import Any
from datetime import date

import pydantic
from ruamel.yaml import YAML
from rendercv.schema.models.cv.cv import Cv
from rendercv.schema.models.design.classic_theme import ClassicTheme
from rendercv.schema.models.rendercv_model import RenderCVModel
from rendercv.schema.models.settings.settings import Settings
from rendercv.schema.sample_generator import dictionary_to_yaml

from .Header import Header
from .Section import Section

ENTRY_METADATA_FIELDS = {"enabled", "include_in", "exclude_from", "tags", "metadata"}


def _get_hugo_executable() -> str:
    try:
        from hugo.cli import HUGO_EXECUTABLE
    except ModuleNotFoundError:
        return "hugo"

    return str(HUGO_EXECUTABLE)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "section"


def _pretty_key(key: str) -> str:
    return key.replace("_", " ").strip().title()


def _entry_to_markdown_lines(entry: Any, *, with_heading: bool) -> tuple[str, list[str]]:
    entry_dict = entry.model_dump(mode="json", exclude_none=True)
    entry_dict = {k: v for k, v in entry_dict.items() if k not in ENTRY_METADATA_FIELDS}

    heading_fields = ("name", "institution", "company", "position", "degree", "label", "title", "bullet")
    heading_value = next((entry_dict.get(field) for field in heading_fields if entry_dict.get(field)), None)
    entry_title = str(heading_value) if heading_value else "Entry"

    lines: list[str] = []
    if heading_value and with_heading:
        lines.append(f"### {heading_value}")

    for key, value in entry_dict.items():
        if heading_value and value == heading_value and key in heading_fields:
            continue
        if key == "highlights":
            highlights = [str(item) for item in (value or [])]
            if highlights:
                lines.append("**Highlights**")
                lines.extend(f"- {item}" for item in highlights)
            continue

        if isinstance(value, list):
            if not value:
                continue
            lines.append(f"**{_pretty_key(key)}**")
            lines.extend(f"- {item}" for item in value)
        elif isinstance(value, dict):
            nested = ", ".join(f"{_pretty_key(k)}: {v}" for k, v in value.items())
            lines.append(f"- **{_pretty_key(key)}:** {nested}")
        else:
            lines.append(f"- **{_pretty_key(key)}:** {value}")

    return entry_title, lines


def _write_hugo_content(
    *,
    site_root: pathlib.Path,
    content_path: pathlib.Path,
    markdown_body: str,
    title: str,
    summary: str,
    draft: bool,
    content_type: str = "cv",
) -> pathlib.Path:
    front_matter = (
        "---\n"
        f'title: "{title}"\n'
        f'date: "{date.today().isoformat()}"\n'
        f'draft: {str(draft).lower()}\n'
        f'type: "{content_type}"\n'
        f'summary: "{summary}"\n'
        "---\n\n"
    )

    target_path = content_path if content_path.is_absolute() else site_root / content_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(front_matter + markdown_body + "\n", encoding="utf-8")
    return target_path


class CV(pydantic.BaseModel):
    """Top-level CV container with a header and an ordered list of sections."""

    header: Header
    sections: list[Section] = pydantic.Field(default_factory=list)

    def _rendercv_sections(self) -> dict[str, list[dict[str, Any]]]:
        rendercv_sections: dict[str, list[dict[str, Any]]] = {}
        for index, section in enumerate(self.sections, start=1):
            base_title = section.title or f"Section {index}"
            section_title = base_title
            disambiguator = 2
            while section_title in rendercv_sections:
                section_title = f"{base_title} {disambiguator}"
                disambiguator += 1

            cleaned_entries = []
            for entry in section.entries:
                if not entry.enabled:
                    continue
                entry_dict = entry.model_dump(mode="json", exclude_none=True)
                entry_dict = {
                    key: value
                    for key, value in entry_dict.items()
                    if key not in ENTRY_METADATA_FIELDS
                }
                cleaned_entries.append(entry_dict)

            rendercv_sections[section_title] = cleaned_entries

        return rendercv_sections

    def get_yaml(self) -> str:
        """Return the YAML representation of this CV."""
        return dictionary_to_yaml(self.model_dump(mode="json", exclude_none=True))

    def _to_rendercv_model(
        self,
        *,
        output_folder: pathlib.Path | None = None,
        typst_path: pathlib.Path | None = None,
        pdf_path: pathlib.Path | None = None,
        markdown_path: pathlib.Path | None = None,
        html_path: pathlib.Path | None = None,
        settings: Settings | None = None,
        design: ClassicTheme | None = None,
    ) -> RenderCVModel:
        cv_payload: dict[str, Any] = self.header.to_cv_kwargs()
        cv_payload["sections"] = self._rendercv_sections()

        rendercv_cv = Cv.model_validate(cv_payload)

        render_settings = settings.model_copy(deep=True) if settings else Settings()
        if output_folder is not None:
            render_settings.render_command.output_folder = output_folder
        if typst_path is not None:
            render_settings.render_command.typst_path = typst_path
        if pdf_path is not None:
            render_settings.render_command.pdf_path = pdf_path
        if markdown_path is not None:
            render_settings.render_command.markdown_path = markdown_path
        if html_path is not None:
            render_settings.render_command.html_path = html_path

        render_design = design.model_copy(deep=True) if design else ClassicTheme()

        return RenderCVModel(
            cv=rendercv_cv,
            design=render_design,
            settings=render_settings,
        )

    def generate_pdf(
        self,
        *,
        output_folder: pathlib.Path | None = None,
        typst_path: pathlib.Path | None = None,
        pdf_path: pathlib.Path | None = None,
        settings: Settings | None = None,
        design: ClassicTheme | None = None,
    ) -> pathlib.Path | None:
        """Generate PDF using RenderCV's native rendering pipeline.

        This method keeps your custom models, converts section entries to
        RenderCV-compatible dictionaries, builds a `RenderCVModel`, and then calls
        RenderCV's own `generate_typst` and `generate_pdf` functions.
        """
        try:
            from rendercv.renderer.pdf_png import generate_pdf as rendercv_generate_pdf
            from rendercv.renderer.typst import generate_typst
        except ModuleNotFoundError as exc:
            message = (
                "RenderCV PDF generation dependencies are missing. Install RenderCV "
                "with full extras (e.g., `pip install \"rendercv[full]\"`)."
            )
            raise RuntimeError(message) from exc

        rendercv_model = self._to_rendercv_model(
            output_folder=output_folder,
            typst_path=typst_path,
            pdf_path=pdf_path,
            settings=settings,
            design=design,
        )
        generated_typst_path = generate_typst(rendercv_model)
        return rendercv_generate_pdf(rendercv_model, generated_typst_path)

    def generate_markdown(
        self,
        *,
        output_folder: pathlib.Path | None = None,
        markdown_path: pathlib.Path | None = None,
        settings: Settings | None = None,
        design: ClassicTheme | None = None,
    ) -> pathlib.Path | None:
        """Generate Markdown using RenderCV's native rendering pipeline."""
        from rendercv.renderer.markdown import generate_markdown as rendercv_generate_markdown

        rendercv_model = self._to_rendercv_model(
            output_folder=output_folder,
            markdown_path=markdown_path,
            settings=settings,
            design=design,
        )
        return rendercv_generate_markdown(rendercv_model)

    def generate_html(
        self,
        *,
        output_folder: pathlib.Path | None = None,
        markdown_path: pathlib.Path | None = None,
        html_path: pathlib.Path | None = None,
        settings: Settings | None = None,
        design: ClassicTheme | None = None,
    ) -> pathlib.Path | None:
        """Generate HTML using RenderCV's native markdown->html pipeline."""
        from rendercv.renderer.html import generate_html as rendercv_generate_html
        from rendercv.renderer.markdown import generate_markdown as rendercv_generate_markdown

        rendercv_model = self._to_rendercv_model(
            output_folder=output_folder,
            markdown_path=markdown_path,
            html_path=html_path,
            settings=settings,
            design=design,
        )
        generated_markdown_path = rendercv_generate_markdown(rendercv_model)
        return rendercv_generate_html(rendercv_model, generated_markdown_path)

    def generate_all(
        self,
        *,
        output_folder: pathlib.Path | None = None,
        typst_path: pathlib.Path | None = None,
        pdf_path: pathlib.Path | None = None,
        markdown_path: pathlib.Path | None = None,
        html_path: pathlib.Path | None = None,
        settings: Settings | None = None,
        design: ClassicTheme | None = None,
    ) -> dict[str, pathlib.Path | None]:
        """Generate all supported outputs using RenderCV's native pipeline.

        Returns a dictionary containing resolved output paths for `typst`, `pdf`,
        `markdown`, and `html`.
        """
        try:
            from rendercv.renderer.html import generate_html as rendercv_generate_html
            from rendercv.renderer.markdown import generate_markdown as rendercv_generate_markdown
            from rendercv.renderer.pdf_png import generate_pdf as rendercv_generate_pdf
            from rendercv.renderer.typst import generate_typst
        except ModuleNotFoundError as exc:
            message = (
                "RenderCV generation dependencies are missing. Install RenderCV "
                "with full extras (e.g., `pip install \"rendercv[full]\"`)."
            )
            raise RuntimeError(message) from exc

        rendercv_model = self._to_rendercv_model(
            output_folder=output_folder,
            typst_path=typst_path,
            pdf_path=pdf_path,
            markdown_path=markdown_path,
            html_path=html_path,
            settings=settings,
            design=design,
        )

        generated_typst_path = generate_typst(rendercv_model)
        generated_pdf_path = rendercv_generate_pdf(rendercv_model, generated_typst_path)
        generated_markdown_path = rendercv_generate_markdown(rendercv_model)
        generated_html_path = rendercv_generate_html(rendercv_model, generated_markdown_path)

        return {
            "typst": generated_typst_path,
            "pdf": generated_pdf_path,
            "markdown": generated_markdown_path,
            "html": generated_html_path,
        }

    def build_hugo_site(
        self,
        *,
        site_root: pathlib.Path,
        content_path: pathlib.Path = pathlib.Path("content/cv/index.md"),
        static_subdir: pathlib.Path = pathlib.Path("static/cv"),
        public_dir: pathlib.Path = pathlib.Path("public"),
        title: str | None = None,
        summary: str | None = None,
        draft: bool = False,
        output_folder: pathlib.Path | None = None,
        typst_path: pathlib.Path | None = None,
        pdf_path: pathlib.Path | None = None,
        settings: Settings | None = None,
        design: ClassicTheme | None = None,
    ) -> dict[str, pathlib.Path | dict[str, pathlib.Path | None]]:
        """Generate CV content/assets and build the Hugo site with the packaged Hugo binary."""
        site_root = pathlib.Path(site_root).resolve()
        site_root.mkdir(parents=True, exist_ok=True)

        config_path = site_root / "hugo.yaml"
        config = self._build_hugo_profile_config(title=title, summary=summary)
        yaml_writer = YAML()
        yaml_writer.default_flow_style = False
        with config_path.open("w", encoding="utf-8") as handle:
            yaml_writer.dump(config, handle)

        old_toml = site_root / "hugo.toml"
        if old_toml.exists():
            old_toml.unlink()

        generated_pdf_path = self.generate_pdf(
            output_folder=output_folder,
            typst_path=typst_path,
            pdf_path=pdf_path,
            settings=settings,
            design=design,
        )
        if generated_pdf_path is None:
            raise RuntimeError("RenderCV PDF generation is disabled.")

        final_title = title or (self.header.name + " - CV" if self.header.name else "Portfolio CV")
        final_summary = summary or self.header.headline or "Portfolio and CV"
        content_output_path = self._write_hugo_section_files(
            site_root=site_root,
            content_path=content_path,
            title=final_title,
            summary=final_summary,
            draft=draft,
        )

        target_dir = static_subdir if static_subdir.is_absolute() else site_root / static_subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        for legacy_asset in target_dir.glob("*"):
            if legacy_asset.is_file() and legacy_asset.suffix.lower() in {".md", ".html", ".typ"}:
                legacy_asset.unlink()

        copied_assets: dict[str, pathlib.Path | None] = {"pdf": None}
        pdf_destination = target_dir / generated_pdf_path.name
        shutil.copy2(generated_pdf_path, pdf_destination)
        copied_assets["pdf"] = pdf_destination

        if typst_path and typst_path.exists():
            typst_path.unlink()

        public_output_path = site_root / public_dir
        hugo_executable = _get_hugo_executable()
        subprocess.run([hugo_executable, "build", "--cleanDestinationDir"], cwd=site_root, check=True)

        return {
            "content": content_output_path,
            "assets": copied_assets,
            "public": public_output_path,
            "outputs": {"pdf": generated_pdf_path},
        }

    def _build_hugo_profile_config(
        self,
        *,
        title: str | None,
        summary: str | None,
    ) -> dict[str, Any]:
        site_title = self.header.name or title or "Portfolio"
        site_description = summary or self.header.headline or "Portfolio and CV"

        return {
            "baseURL": "http://localhost:1313/",
            "languageCode": "en-us",
            "title": site_title,
            "theme": "hugo-profile",
            "enableEmoji": True,
            "markup": {
                "goldmark": {"renderer": {"unsafe": True}},
            },
            "menu": {
                "main": [
                    {"name": "About", "url": "/about/", "weight": 1},
                    {"name": "CV", "url": "/cv/", "weight": 1},
                    {"name": "Contact", "url": "/contact/", "weight": 2},
                    {"name": "PDF", "url": "/cv/sample_cv.pdf", "weight": 3},
                ]
            },
            "params": {
                "title": site_title,
                "description": site_description,
                "hostName": "http://localhost:1313",
                "staticPath": "",
                "favicon": "",
                "copyright": site_title,
                "animate": True,
                "theme": {"disableThemeToggle": False},
                "navbar": {
                    "align": "ms-auto",
                    "disableSearch": True,
                    "brandLogo": "",
                    "stickyNavBar": {"enable": True, "showOnScrollUp": True},
                    "menus": {
                        "disableAbout": True,
                        "disableExperience": True,
                        "disableEducation": True,
                        "disableProjects": True,
                        "disableAchievements": True,
                        "disableContact": True,
                    },
                },
                "hero": {"enable": False},
                "about": {"enable": False},
                "experience": {"enable": False},
                "education": {"enable": False},
                "projects": {"enable": False},
                "achievements": {"enable": False},
                "contact": {"enable": False},
            },
        }

    def _write_hugo_section_files(
        self,
        *,
        site_root: pathlib.Path,
        content_path: pathlib.Path,
        title: str,
        summary: str,
        draft: bool,
    ) -> pathlib.Path:
        root_content_path = content_path if content_path.is_absolute() else site_root / content_path
        if root_content_path.name == "index.md":
            root_content_path = root_content_path.with_name("_index.md")
        cv_dir = root_content_path.parent if root_content_path.suffix == ".md" else root_content_path
        cv_dir.mkdir(parents=True, exist_ok=True)

        section_slugs = [_slugify(section.title or f"section-{index}") for index, section in enumerate(self.sections, start=1)]
        for legacy_file in cv_dir.glob("*.md"):
            if legacy_file.name != "_index.md":
                legacy_file.unlink()
        for section_slug in section_slugs:
            section_dir = cv_dir / section_slug
            if section_dir.exists() and section_dir.is_dir():
                shutil.rmtree(section_dir)

        content_root = cv_dir.parent
        home_index = content_root / "_index.md"
        about_path = content_root / "about" / "index.md"
        contact_path = content_root / "contact" / "index.md"

        about_lines = [summary]
        if self.header.headline:
            about_lines.append("")
            about_lines.append(f"Current role: {self.header.headline}")
        if self.header.location:
            about_lines.append(f"Location: {self.header.location}")

        contact_lines = ["You can reach me through the following channels:"]
        emails = self.header.email if isinstance(self.header.email, list) else ([self.header.email] if self.header.email else [])
        for email in emails:
            contact_lines.append(f"- Email: [{email}](mailto:{email})")
        phones = self.header.phone if isinstance(self.header.phone, list) else ([self.header.phone] if self.header.phone else [])
        for phone in phones:
            contact_lines.append(f"- Phone: {phone}")
        if self.header.location:
            contact_lines.append(f"- Location: {self.header.location}")
        if self.header.website:
            websites = self.header.website if isinstance(self.header.website, list) else [self.header.website]
            for website in websites:
                contact_lines.append(f"- Website: {website}")
        if self.header.social_networks:
            for social in self.header.social_networks:
                contact_lines.append(f"- {social.network}: {social.username}")

        _write_hugo_content(
            site_root=site_root,
            content_path=about_path,
            markdown_body="\n".join(about_lines),
            title="About",
            summary="About me",
            draft=draft,
            content_type="page",
        )

        _write_hugo_content(
            site_root=site_root,
            content_path=contact_path,
            markdown_body="\n".join(contact_lines),
            title="Contact",
            summary="How to contact me",
            draft=draft,
            content_type="page",
        )

        home_body = "\n".join(
            [
                summary,
                "",
                "## Pages",
                "- [About](/about/)",
                "- [CV](/cv/)",
                "- [Contact](/contact/)",
            ]
        )
        _write_hugo_content(
            site_root=site_root,
            content_path=home_index,
            markdown_body=home_body,
            title=self.header.name or "Portfolio",
            summary=summary,
            draft=draft,
            content_type="home",
        )

        section_links: list[str] = []
        if self.sections:
            for index, section in enumerate(self.sections, start=1):
                section_title = section.title or _pretty_key(f"section {index}")
                section_slug = _slugify(section_title or f"section-{index}")
                section_dir = cv_dir / section_slug
                section_dir.mkdir(parents=True, exist_ok=True)

                entry_links: list[str] = []
                enabled_entries = [entry for entry in section.entries if getattr(entry, "enabled", True)]
                for index, entry in enumerate(enabled_entries, start=1):
                    entry_title, entry_lines = _entry_to_markdown_lines(entry, with_heading=False)
                    entry_slug = f"{index:02d}-{_slugify(entry_title)}"
                    entry_rel_path = f"{entry_slug}/"
                    entry_links.append(f"- [{entry_title}]({entry_rel_path})")

                    entry_page_body = "\n".join(entry_lines).strip() or "No details available."
                    entry_file = section_dir / f"{entry_slug}.md"
                    _write_hugo_content(
                        site_root=site_root,
                        content_path=entry_file,
                        markdown_body=entry_page_body,
                        title=entry_title,
                        summary=f"{section_title} entry",
                        draft=draft,
                    )

                section_index_body = [f"Browse {section_title} entries.", "", "## Entries"]
                section_index_body.extend(entry_links or ["- No entries yet."])
                _write_hugo_content(
                    site_root=site_root,
                    content_path=section_dir / "_index.md",
                    markdown_body="\n".join(section_index_body),
                    title=section_title,
                    summary=f"{section_title} section",
                    draft=draft,
                )

                section_links.append(f"- [{section_title}]({section_slug}/)")

        cv_index_body = [summary, "", "## Sections"]
        cv_index_body.extend(section_links or ["- CV sections will appear here."])
        cv_index_body.extend(
            [
                "",
                "## Downloads",
                "- [PDF](/cv/sample_cv.pdf)",
            ]
        )

        return _write_hugo_content(
            site_root=site_root,
            content_path=cv_dir / "_index.md",
            markdown_body="\n".join(cv_index_body),
            title=title,
            summary=summary,
            draft=draft,
        )

