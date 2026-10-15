
"""
Smart Process Guardian - Prototype Collector and Detector
Appendix A: Generate Code

NOTE:
This version uses synthetic process data.
It does not collect live operating-system metrics.
"""

import time
import random
import statistics
import json
from collections import deque


class ProcessSample:
    def __init__(self, pid, cpu, mem, io_wait):
        self.pid = pid
        self.cpu = cpu
        self.mem = mem
        self.io_wait = io_wait
        self.ts = time.time()

    def to_dict(self):
        return {
            "pid": self.pid,
            "cpu": self.cpu,
            "mem": self.mem,
            "io_wait": self.io_wait,
            "ts": round(self.ts, 3)
        }


class SyntheticProcessReader:
    """Generate simulated process metrics for testing."""

    def __init__(self, pid, workload="normal"):
        self.pid = pid
        self.workload = workload

    def read(self):
        if self.workload == "cpu":
            cpu = random.uniform(70, 95)
            mem = random.uniform(20, 40)
            io = random.uniform(0, 5)

        elif self.workload == "memory":
            cpu = random.uniform(5, 20)
            mem = random.uniform(80, 95)
            io = random.uniform(0, 5)

        elif self.workload == "io":
            cpu = random.uniform(10, 30)
            mem = random.uniform(20, 40)
            io = random.uniform(40, 80)

        else:
            cpu = random.uniform(2, 10)
            mem = random.uniform(10, 25)
            io = random.uniform(0, 3)

        return ProcessSample(
            self.pid,
            round(cpu, 2),
            round(mem, 2),
            round(io, 2)
        )


class RollingHistory:
    def __init__(self, maxlen=500):
        self.values = deque(maxlen=maxlen)

    def add(self, value):
        self.values.append(value)

    def mean(self):
        return statistics.mean(self.values) if self.values else 0

    def stdev(self):
        return (
            statistics.pstdev(self.values)
            if len(self.values) > 1 else 0
        )

    def __len__(self):
        return len(self.values)


class ThresholdDetector:
    def __init__(self, cpu=80, mem=85, io=60):
        self.limits = {
            "cpu": cpu,
            "mem": mem,
            "io_wait": io
        }

    def detect(self, sample):
        values = {
            "cpu": sample.cpu,
            "mem": sample.mem,
            "io_wait": sample.io_wait
        }

        return [
            metric for metric, value in values.items()
            if value > self.limits[metric]
        ]


class ZScoreDetector:
    def __init__(self, history, threshold=3.0, min_samples=10):
        self.history = history
        self.threshold = threshold
        self.min_samples = min_samples

    def detect(self, value):
        # Avoid unreliable detection with insufficient history.
        if len(self.history) < self.min_samples:
            return False

        mean = self.history.mean()
        stdev = self.history.stdev()

        if stdev == 0:
            return False

        z_score = abs(value - mean) / stdev
        return z_score > self.threshold


class GuardianAgent:
    def __init__(self, readers, history_len=500):
        self.readers = readers

        self.histories = {
            reader.pid: {
                "cpu": RollingHistory(history_len),
                "mem": RollingHistory(history_len),
                "io_wait": RollingHistory(history_len)
            }
            for reader in readers
        }

        self.threshold_detector = ThresholdDetector()

        self.zscore_detectors = {
            reader.pid: {
                metric: ZScoreDetector(
                    self.histories[reader.pid][metric]
                )
                for metric in ("cpu", "mem", "io_wait")
            }
            for reader in readers
        }

    def cycle(self):
        samples = []
        alerts = []

        for reader in self.readers:
            sample = reader.read()
            sample_data = sample.to_dict()
            samples.append(sample_data)

            values = {
                "cpu": sample.cpu,
                "mem": sample.mem,
                "io_wait": sample.io_wait
            }

            # Check against previous history before updating it.
            threshold_flags = self.threshold_detector.detect(sample)
            anomaly_flags = [
                metric
                for metric, value in values.items()
                if self.zscore_detectors[reader.pid][metric].detect(value)
            ]

            reasons = sorted(set(threshold_flags + anomaly_flags))

            if reasons:
                alerts.append({
                    "pid": reader.pid,
                    "reason": reasons,
                    "sample": sample_data
                })

            # Update all histories after detection.
            for metric, value in values.items():
                self.histories[reader.pid][metric].add(value)

        return {"samples": samples, "alerts": alerts}


if __name__ == "__main__":
    random.seed(42)  # Reproducible demonstration output.

    readers = [
        SyntheticProcessReader(101, "normal"),
        SyntheticProcessReader(102, "cpu"),
        SyntheticProcessReader(103, "memory"),
        SyntheticProcessReader(104, "io")
    ]

    agent = GuardianAgent(readers)

    sampling_interval = 0.2  # Demo only; use 10 for the handbook test.

    try:
        for cycle_number in range(3):
            result = agent.cycle()

            print(f"\n--- Cycle {cycle_number + 1} ---")
            print(json.dumps(result, indent=2))

            if cycle_number < 2:
                time.sleep(sampling_interval)

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
