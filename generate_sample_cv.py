from __future__ import annotations

from pathlib import Path

from models import CV, Section
from models.entries.Awards import Awards
from models.entries.Education import Education
from models.entries.Experience import Experience
from models.entries.Project import Project
from models.entries.Skills import Skills


def build_sample_cv() -> CV:
    return CV(
        name="Mohammad Mahdi Vahedi",
        headline="Data Infrastructure Engineer",
        location="Tehran, Iran",
        email="m.m.vahedi13800@gmail.com",
        phone="+989205175411",
        sections={
            "education": Section(
                title="Education",
                entries=[
                    Education(
                        institution="Sharif University of Technology",
                        area="Artificial Intelligence and Robotics",
                        degree="Master",
                        start_date="2024",
                        end_date="present",
                        location="Tehran",
                    ),
                    Education(
                        institution="Sharif University of Technology",
                        area="Computer Engineering",
                        degree="Bachelor",
                        start_date="2020",
                        end_date="2024",
                        location="Tehran",
                        highlights=["GPA: 19.5/20"],
                    ),
                ],
            ),
            "experience": Section(
                title="Experience",
                entries=[
                    Experience(
                        company="MCI Next (Hamrah e Aval)",
                        position="Junior Data Infrastructure Engineer - Part Time",
                        start_date="2023-12",
                        end_date="present",
                        location="Tehran",
                        highlights=[
                            "Worked on data infrastructure and platform reliability."
                        ],
                    )
                ],
            ),
            "projects": Section(
                title="Projects",
                entries=[
                    Project(
                        name="Rudabeh (Multi-Tenant Apache Kafka)",
                        date="Spring & Summer 2024",
                        highlights=[
                            "Led development of multi-tenant Kafka on Kubernetes.",
                            "Reduced infrastructure waste and improved service maintenance.",
                        ],
                    )
                ],
            ),
            "skills": Section(
                title="Skills",
                entries=[
                    Skills(label="Programming", details="Python, Java, C/C++"),
                    Skills(
                        label="Software",
                        details="Kubernetes, Docker, Apache Kafka, PostgreSQL, ClickHouse",
                    ),
                ],
            ),
            "awards": Section(
                title="Awards",
                entries=[
                    Awards(
                        bullet="Gold medal, National Astronomy and Astrophysics Olympiad (2019)"
                    )
                ],
            ),
        },
    )


def main() -> None:
    cv = build_sample_cv()

    sample_yaml_path = Path("sample_cv.yaml")
    sample_yaml_path.write_text(f"cv:\n{cv.get_yaml()}", encoding="utf-8")

    markdown_path = cv.generate_markdown(
        output_folder=Path("build"),
        markdown_path=Path("build/sample_cv.md"),
    )

    html_path = cv.generate_html(
        output_folder=Path("build"),
        markdown_path=Path("build/sample_cv.md"),
        html_path=Path("build/sample_cv.html"),
    )

    pdf_path = None
    try:
        pdf_path = cv.generate_pdf(
            output_folder=Path("build"),
            pdf_path=Path("build/sample_cv.pdf"),
            typst_path=Path("build/sample_cv.typ"),
        )
    except Exception as exc:
        print(f"PDF generation skipped: {exc}")

    print(f"YAML written to: {sample_yaml_path.resolve()}")
    print(f"Markdown written to: {markdown_path.resolve() if markdown_path else 'None'}")
    print(f"HTML written to: {html_path.resolve() if html_path else 'None'}")
    print(f"PDF written to: {pdf_path.resolve() if pdf_path else 'None'}")


if __name__ == "__main__":
    main()
