# QualityGuard AI — Fastener Quality Control Agent

An autonomous, rule-based agentic workflow for incoming-batch inspection of
**M8 x 30 mm Socket Head Cap Screws (Grade 12.9, ISO 4762)**.

For each critical dimension (thread pitch diameter, shank length, head diameter) the agent:

1. Reads CMM measurement samples
2. Checks every part against the lower/upper specification limits
3. Computes mean, standard deviation, defect rate and process capability (Cpk)
4. Decides PASS / WARNING / CRITICAL and recommends a corrective action
5. Issues an overall batch disposition (release, 100% sorting, or quarantine)

## Run

```bash
python qualityguard_screws.py
```

Requires Python 3.8+ and only the standard library.

## Decision logic

| Condition | Status |
|---|---|
| Defect rate > 5% | CRITICAL - batch rejection |
| 0% < defect rate <= 5% | WARNING - rework / sorting |
| No defects but Cpk < 1.0 | WARNING - high process variation |
| Otherwise | PASS |

## Sample result

The simulated head-diameter data (die wear) pushes 6 of 10 parts above the upper limit,
so the agent rejects and quarantines the batch.
