from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ztbd.config import DatabaseTarget


ScenarioOperation = Callable[[Any], dict]
ScenarioExplain = Callable[[Any], str | None]


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    name: str
    supported_targets: set[DatabaseTarget]
    operation_by_target: dict[DatabaseTarget, ScenarioOperation]
    explain_by_target: dict[DatabaseTarget, ScenarioExplain] | None = None
    mutating: bool = False

    def supports(self, target: DatabaseTarget) -> bool:
        return target in self.supported_targets and target in self.operation_by_target

    def operation_for(self, target: DatabaseTarget) -> ScenarioOperation:
        return self.operation_by_target[target]

    def explain_for(self, target: DatabaseTarget) -> ScenarioExplain | None:
        if self.explain_by_target is None:
            return None
        return self.explain_by_target.get(target)
