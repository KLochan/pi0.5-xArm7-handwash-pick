#!/usr/bin/env python3
import csv
import math
import statistics
import sys


def as_float(value):
    value = value.strip()
    return float(value) if value else None


def as_int(value):
    value = value.strip()
    return int(value) if value else None


def main(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("No evaluation trials found.")
        return

    successes = []
    task_times = []
    mean_latencies = []
    min_latencies = []
    max_latencies = []
    policy_calls = []

    for row in rows:
        success_text = row["success"].strip().lower()
        success = success_text in {"1", "true", "yes", "y", "success"}
        successes.append(success)

        for key, target in [
            ("task_time_s", task_times),
            ("mean_inference_ms", mean_latencies),
            ("min_inference_ms", min_latencies),
            ("max_inference_ms", max_latencies),
        ]:
            value = as_float(row[key])
            if value is not None and math.isfinite(value):
                target.append(value)

        calls = as_int(row["policy_calls"])
        if calls is not None:
            policy_calls.append(calls)

    total = len(rows)
    success_count = sum(successes)
    success_rate = 100.0 * success_count / total

    print(f"Trials: {total}")
    print(f"Successes: {success_count}")
    print(f"Success rate: {success_rate:.1f}%")

    if task_times:
        print(f"Mean task time: {statistics.mean(task_times):.3f} s")
        print(f"Min task time: {min(task_times):.3f} s")
        print(f"Max task time: {max(task_times):.3f} s")

    if mean_latencies:
        print(f"Mean inference latency: {statistics.mean(mean_latencies):.3f} ms")

    if min_latencies:
        print(f"Minimum observed inference latency: {min(min_latencies):.3f} ms")

    if max_latencies:
        print(f"Maximum observed inference latency: {max(max_latencies):.3f} ms")

    if policy_calls:
        print(f"Mean policy calls per trial: {statistics.mean(policy_calls):.2f}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 evaluation/summarize_results.py evaluation/trials.csv")
        raise SystemExit(2)
    main(sys.argv[1])
