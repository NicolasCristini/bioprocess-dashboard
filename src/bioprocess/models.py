"""Input data model (MODEL.md §1). Pure pydantic; no UI imports."""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = 1
MAX_PHASES = 6
MAX_DAYS = 120
REGIME_DAYS = 30

FeedSetting = Union[float, Literal["= bleed", "suggested"]]
BleedSetting = Union[float, Literal["suggested"]]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Setup(_Model):
    vessel_volume_L: float = Field(2.0, gt=0)
    initial_wv_L: float = Field(1.0, gt=0)
    v_min_L: float = Field(0.5, ge=0)
    v_max_L: float = Field(2.0, gt=0)
    seeding_density: float = Field(8.0e5, gt=0, description="cells/mL at t = 0")
    wet_biomass_g_per_L_at_1e6: float = Field(2.0, ge=0)
    steps_per_day: int = Field(24, ge=1, le=96)


class Metabolite(_Model):
    name: str
    kind: Literal["consumed", "produced"]
    q: float | None = Field(None, description="1E-11 mmol/cell/h; None = not modelled")
    limit: float | None = None
    c_batch: float | None = None
    c_fedbatch: float | None = None
    c_perfusion: float | None = None

    @property
    def sign(self) -> int:
        return -1 if self.kind == "consumed" else 1

    @property
    def modelled(self) -> bool:
        return self.q is not None and self.c_batch is not None


class FeedRegime(_Model):
    name: str
    description: str = ""
    pct_per_day: dict[int, float] = Field(default_factory=dict,
                                          description="phase day (1-30) -> % of V0 fed that day")

    def pct(self, day: int) -> float:
        return float(self.pct_per_day.get(day, 0.0) or 0.0)


class BatchPhase(_Model):
    type: Literal["Batch"] = "Batch"
    days: int = Field(gt=0)
    mu: float


class FedBatchPhase(_Model):
    type: Literal["Fed-batch"] = "Fed-batch"
    days: int = Field(gt=0)
    mu: float
    regime: str


class ContinuousPhase(_Model):
    type: Literal["Continuous"] = "Continuous"
    days: int = Field(gt=0)
    mu: float
    bleed_vvd: BleedSetting = "suggested"
    feed_vvd: FeedSetting = "= bleed"


Phase = Annotated[Union[BatchPhase, FedBatchPhase, ContinuousPhase], Field(discriminator="type")]
PHASE_TYPES = {"Batch": BatchPhase, "Fed-batch": FedBatchPhase, "Continuous": ContinuousPhase}


class Scenario(_Model):
    schema_version: int = SCHEMA_VERSION
    name: str = "Untitled scenario"
    notes: str = ""
    setup: Setup = Field(default_factory=Setup)
    metabolites: list[Metabolite]
    regimes: list[FeedRegime]
    phases: list[Phase]

    def regime(self, name: str) -> FeedRegime | None:
        return next((r for r in self.regimes if r.name == name), None)

    @property
    def total_days(self) -> int:
        return sum(p.days for p in self.phases)
