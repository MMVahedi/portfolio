from __future__ import annotations

import pathlib
from typing import Any

import pydantic
from rendercv.schema.models.cv.cv import Cv
from rendercv.schema.models.rendercv_model import RenderCVModel
from rendercv.schema.models.settings.settings import Settings
from rendercv.schema.sample_generator import dictionary_to_yaml

from .Section import Section

ENTRY_METADATA_FIELDS = {"enabled", "include_in", "exclude_from", "tags", "metadata"}


class CV(Cv):
    """Top-level CV container with named sections.

    Each section contains a list of concrete entry objects derived from the shared
    `Entry` base class.
    """

    sections: dict[str, Section] | None = pydantic.Field(default=None)

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
    ) -> RenderCVModel:
        cv_payload: dict[str, Any] = self.model_dump(mode="json", exclude_none=True)

        if self.sections is not None:
            rendercv_sections: dict[str, list[dict]] = {}
            for fallback_title, section in self.sections.items():
                section_title = section.title or fallback_title
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

            cv_payload["sections"] = rendercv_sections

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

        return RenderCVModel(cv=rendercv_cv, settings=render_settings)

    def generate_pdf(
        self,
        *,
        output_folder: pathlib.Path | None = None,
        typst_path: pathlib.Path | None = None,
        pdf_path: pathlib.Path | None = None,
        settings: Settings | None = None,
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
        )
        generated_typst_path = generate_typst(rendercv_model)
        return rendercv_generate_pdf(rendercv_model, generated_typst_path)

    def generate_markdown(
        self,
        *,
        output_folder: pathlib.Path | None = None,
        markdown_path: pathlib.Path | None = None,
        settings: Settings | None = None,
    ) -> pathlib.Path | None:
        """Generate Markdown using RenderCV's native rendering pipeline."""
        from rendercv.renderer.markdown import generate_markdown as rendercv_generate_markdown

        rendercv_model = self._to_rendercv_model(
            output_folder=output_folder,
            markdown_path=markdown_path,
            settings=settings,
        )
        return rendercv_generate_markdown(rendercv_model)

    def generate_html(
        self,
        *,
        output_folder: pathlib.Path | None = None,
        markdown_path: pathlib.Path | None = None,
        html_path: pathlib.Path | None = None,
        settings: Settings | None = None,
    ) -> pathlib.Path | None:
        """Generate HTML using RenderCV's native markdown->html pipeline."""
        from rendercv.renderer.html import generate_html as rendercv_generate_html
        from rendercv.renderer.markdown import generate_markdown as rendercv_generate_markdown

        rendercv_model = self._to_rendercv_model(
            output_folder=output_folder,
            markdown_path=markdown_path,
            html_path=html_path,
            settings=settings,
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

