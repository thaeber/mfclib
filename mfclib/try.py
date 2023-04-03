#%%
from typing import Dict
import mfclib
import dataclasses

mixture = dict(Ar=85.08, CO=14.92, NO=0.0)
cf = mfclib.calculate_CF(mixture)
cf


# %%
@dataclasses.dataclass(frozen=True)
class Source:
    name: str
    composition: Dict[str, float] = dataclasses.field(default_factory=dict)


sources = [
    Source('Carrier Gas', composition=dict(Ar=1.0)),
    Source('O2', composition=dict(O2=1.0)),
    Source('CO', composition=dict(CO=0.1492, Ar=0.8508)),
    Source('NO', composition=dict(NO=0.002959, Ar=0.997041)),
]
sources

# %%
