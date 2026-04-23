from __future__ import annotations

from typing import Any

from rendercv.schema.models.cv.entries.bases.entry import BaseEntry
from rendercv.schema.sample_generator import dictionary_to_yaml


class Entry(BaseEntry):
    """Shared base class for all CV entries."""

    enabled: bool = True
    include_in: list[str] | None = None
    exclude_from: list[str] | None = None
    tags: list[str] = []
    metadata: dict[str, Any] = {}

    def get_yaml(self) -> str:
        """Return the YAML representation of this entry.

        The output includes the full entry data for the model, including the shared
        versioning metadata fields defined on `Entry`.
        """
        return dictionary_to_yaml(self.model_dump(mode="json", exclude_none=True))
