from __future__ import annotations

from typing import Any

from ruamel.yaml import YAML
from rendercv.schema.models.cv.entries.bases.entry import BaseEntry
from rendercv.schema.sample_generator import dictionary_to_yaml


_yaml = YAML(typ="safe")


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

    @classmethod
    def from_yaml(cls, yaml_text: str) -> "Entry":
        """Create an entry object from its YAML representation."""
        data = _yaml.load(yaml_text)

        if data is None:
            raise ValueError("YAML content is empty.")

        if not isinstance(data, dict):
            raise ValueError("YAML content must represent a mapping/object.")

        return cls.model_validate(data)
