import pydantic
from .mixture import Mixture


class MFCLine(pydantic.BaseModel):
    name: str
    gas: Mixture

    @pydantic.field_validator('gas', mode='before')
    @classmethod
    def check_composition(cls, value):
        return Mixture.create(value)
