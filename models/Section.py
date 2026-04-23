from __future__ import annotations

import pydantic

from rendercv.schema.models.cv.section import BaseRenderCVSection
from rendercv.schema.sample_generator import dictionary_to_yaml

from .entries.Entry import Entry


class Section(BaseRenderCVSection):
    """Container for one CV section with multiple objects."""

    title: str
    entry_type: str = "Mixed"
    entries: list[Entry] = pydantic.Field(default_factory=list)

    def get_yaml(self) -> str:
        """Return the YAML representation of this section."""
        return dictionary_to_yaml(self.model_dump(mode="json", exclude_none=True))

