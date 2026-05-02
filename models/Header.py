from __future__ import annotations

import pydantic
from rendercv.schema.models.cv.cv import ExistingPathRelativeToInput
from rendercv.schema.models.cv.custom_connection import CustomConnection
from rendercv.schema.models.cv.social_network import SocialNetwork
from pydantic import EmailStr
from pydantic.networks import HttpUrl
from rendercv.schema.sample_generator import dictionary_to_yaml


class Header(pydantic.BaseModel):
    """Top-of-CV identity and contact data.

    This mirrors the non-section fields from RenderCV's `Cv` model.
    """

    name: str
    headline: str | None = None
    location: str | None = None
    email: EmailStr | list[EmailStr] | None = None
    photo: ExistingPathRelativeToInput | HttpUrl | None = None
    phone: str | None = None
    website: HttpUrl | list[HttpUrl] | None = None
    social_networks: list[SocialNetwork] | None = None
    custom_connections: list[CustomConnection] | None = None

    def to_cv_kwargs(self) -> dict[str, object]:
        """Return keyword args compatible with `CV(...)` construction."""
        return self.model_dump(mode="json", exclude_none=True)

    def get_yaml(self) -> str:
        """Return the YAML representation of this header."""
        return dictionary_to_yaml(self.model_dump(mode="json", exclude_none=True))
