from __future__ import annotations

from pathlib import Path

from rendercv.schema.models.design.classic_theme import (
    ClassicTheme,
    Sections,
    Entries,
    Page,
    Summary,
    Colors,
    Color,
    Header,
    Typography,
    FontSize,
    FontFamily,
    Highlights,
    Templates,
    PublicationEntry,
    Connections,
    Links,
)

from models import CV
from sections.achievements_and_awards import achievements_and_awards_section
from sections.education import education
from sections.experience import experience_section
from sections.header import header
from sections.languages import languages_section
from sections.interests import interests_section
from sections.projects import projects_section
from sections.publications import publications_section
from sections.skills import skills_section


def resume_design() -> ClassicTheme:
    """RenderCV classic theme tuned for this CV.

    Publications and projects use no right-hand date column so summaries use the
    full content width. Experience and education dates are folded into the main
    column so the global date column width can be zero without losing dates.
    """
    color = Color("rgb(20, 110, 140)")
    font = "Open Sans"
    return ClassicTheme(
        entries=Entries(
            short_second_row=False,
            degree_width="0.5cm",
            summary=Summary(
                space_left="0.2cm",
                space_above="0.1cm",
            ),
            highlights=Highlights(
                space_left="0.2cm",
                space_above="0.1cm",
                space_between_items="0.05cm",
            ),
        ),
        colors=Colors(
            name=color,
            headline=color,
            connections=color,
            section_titles=color,
            links=Color("rgb(0, 0, 0)"),
        ),
        sections=Sections(
            space_between_regular_entries="0.2cm",
            show_time_spans_in=[],
        ),
        page=Page(
            show_footer=False,
            show_top_note=False,
        ),
        header=Header(
            photo_width="3cm",
            connections=Connections(
                space_between_connections="0.2cm",
            ),
        ),
        typography=Typography(
            line_spacing="0.2cm",
            font_size=FontSize(
                name="25pt",
                section_titles="12pt",
                body="9pt"
            ),
            font_family=FontFamily(
                body=font,
                name=font,
                headline=font,
                connections=font,
                section_titles=font,
            ),
        ),
        templates=Templates(
            publication_entry=PublicationEntry(
                main_column="TITLE\nSUMMARY\n**Journal**: JOURNAL\n**Authors**: *AUTHORS*",
            ),
        ),
        links=Links(
            show_external_link_icon=True,
        ),
    )


def build_sample_cv() -> CV:
    return CV(
        header=header,
        sections=[
            education,
            experience_section,
            achievements_and_awards_section,
            publications_section,
            projects_section,
            skills_section,
            interests_section,
            languages_section,
        ],
    )



def main() -> None:
    cv = build_sample_cv()

    build_dir = Path("build")
    build_dir.mkdir(parents=True, exist_ok=True)
    cv.generate_pdf(output_folder=build_dir, design=resume_design())

if __name__ == "__main__":
    main()
