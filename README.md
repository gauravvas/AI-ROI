# AI ROI Framework

A Python reference implementation of Observed Baseline Discovery (OBD), Graph-Weighted Effort Reconstruction (GWER), and Rework-Adjusted Attribution (RAA), based on Gaurav Vashisht's three-stage enterprise AI ROI framework.

This repository is a new explanatory implementation. It reproduce the original paper's experiments and  establish historical savings.

## Run

Python 3.10 or newer. No external packages or API keys required.

```sh
python3 model.py
python3 agents.py
python3 -m unittest -v test_model.py
```

The model generates `sample_data/` and writes results to `results/`. The agent coordinator writes `results/agent_run.json`. These generated folders are ignored by Git; regenerate them with the commands above.

## Worked example

| Measure | Synthetic result |
|---|---:|
| Completed manual / assisted tasks | 100 / 100 |
| Manual baseline per task | 3.9 hours |
| Manual-equivalent human work | 390 hours |
| Assisted human work, including review and rework | 120 hours |
| Released capacity | 270 hours (69.23%) |
| Gross capacity value at assumed $100/hour | $27,000 |
| Assumed incremental AI cost | $500 |
| Capacity value less AI cost | $26,500 |

These are constructed sample outcomes, not verified cash savings or causal field estimates. Counting only 30 hours of machine runtime would overstate savings by 90 hours.

## Components

- `model.py`: baseline calculation, resource graph, attribution rule, fixture generation and numerical outputs.
- `agents.py`: bounded deterministic action/observation controller. No LLM is invoked.
- `test_model.py`: 19 tests for calculations and boundary behavior.
- `ARCHITECTURE.md`: the proposed telemetry-to-measurement integration and its boundaries.

OBD sums median manual step durations and requires at least five complete manual runs. GWER reports a resource-effort index with a channel factor. RAA reports contribution credit adjusted for major rewrites and repeats. Keep effort index, credit, observed human labor and monetary value in separate fields.

## Scope and limitations

The example assumes one workflow, comparable complexity, complete activity capture and equivalent accepted quality. It is not a production field-data importer. Real integrations require identity resolution, idle-time rules, workflow/version matching, acceptance checks, cost reconciliation and data governance. The implementation follows the paper's RAA equation where its prose is ambiguous.

The repository contains the numerical implementation and generated-data recipe. Private correspondence, company telemetry, evidence documents and recordings are maintained separately.

No open-source license has been selected for this repository.
