"""
Base Pydantic class with JSON aliasing, used in the UKRDC API
"""

from pydantic import BaseModel, ConfigDict


def _to_camel(snake_str: str) -> str:
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class JSONModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
    )
