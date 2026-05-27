from typing import Any

from app.eval.scenarios import DEFAULT_L1_SCENARIOS, DEFAULT_PROCESS_GOALS, EvalScenario, ProcessGoalSpec

_LAZY_EXPORTS = {
    "run_cross_domain_adapter_scenarios": ("app.eval.domain_adapter", "run_cross_domain_adapter_scenarios"),
    "run_evidence_robustness_scenarios": ("app.eval.evidence_robustness", "run_evidence_robustness_scenarios"),
    "run_process_fidelity_scenarios": ("app.eval.runner", "run_process_fidelity_scenarios"),
    "run_rule_scenarios": ("app.eval.runner", "run_rule_scenarios"),
    "run_stability_determinism_check": ("app.eval.runner", "run_stability_determinism_check"),
    "run_stability_scenarios": ("app.eval.runner", "run_stability_scenarios"),
}

__all__ = [
    "DEFAULT_L1_SCENARIOS",
    "DEFAULT_PROCESS_GOALS",
    "EvalScenario",
    "ProcessGoalSpec",
    "run_cross_domain_adapter_scenarios",
    "run_evidence_robustness_scenarios",
    "run_process_fidelity_scenarios",
    "run_rule_scenarios",
    "run_stability_determinism_check",
    "run_stability_scenarios",
]


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    module = __import__(module_name, fromlist=[attribute_name])
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
