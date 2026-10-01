# Evaluation Protocol

This folder is for **post-training evaluation**, separate from the approximately 100 demonstrations used for training.

## Recommended protocol

Run a fixed set of independent evaluation trials (for example, 20–30 trials) with the bottle placed at varied initial positions that are not simply replays of the training demonstrations.

For each trial, record:

- trial ID,
- success or failure,
- end-to-end task time,
- mean inference latency,
- minimum inference latency,
- maximum inference latency,
- number of policy calls,
- failure reason (if any),
- optional notes.

## Success criterion

A trial is counted as successful when the robot:

1. approaches the bottle,
2. achieves a stable grasp,
3. lifts the bottle,
4. maintains the grasp for the required hold period.

Use the same success criterion for every trial.

## Files

- `trials.csv`: trial-by-trial evaluation log.
- `summarize_results.py`: computes aggregate success rate and timing statistics.

## Example workflow

1. Run one evaluation trial.
2. Add one row to `trials.csv`.
3. Repeat for all trials.
4. Run:

```bash
python3 evaluation/summarize_results.py evaluation/trials.csv
```

The script will print the aggregate metrics that can be copied into the README after the evaluation is complete.
