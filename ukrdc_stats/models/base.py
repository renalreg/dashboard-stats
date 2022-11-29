"""
Base Pydantic class with JSON aliasing, used in the UKRDC API
"""

from pydantic import BaseModel


def _to_camel(snake_str: str) -> str:
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class JSONModel(BaseModel):
    class Config:
        alias_generator = _to_camel
        allow_population_by_field_name = True
