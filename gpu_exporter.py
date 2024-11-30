#!/usr/bin/python3

import argparse
import os
import subprocess
import time
from collections import defaultdict

from prometheus_client import Gauge, start_http_server

# Prometheus metrics
gpu_memory_usage_gauge = Gauge(
    "gpu_memory_usage", "GPU Memory Usage (MiB)", ["gpu_index", "gpu_uuid"]
)
gpu_user_memory_usage_gauge = Gauge(
    "gpu_user_memory_usage", "User Memory Usage (MiB)", ["user", "gpu_index"]
)
gpu_process_memory_usage_gauge = Gauge(
    "gpu_process_memory_usage",
    "Process Memory Usage (MiB)",
    ["pid", "user", "gpu_index", "process_name"],
)
gpu_utilization_gauge = Gauge(
    "gpu_utilization", "GPU Utilization (%)", ["gpu_index", "gpu_uuid"]
)
gpu_process_utilization_gauge = Gauge(
    "gpu_process_utilization",
    "Process GPU Utilization (%)",
    ["pid", "user", "gpu_index", "process_name"],
)


def nvidia_smi(query, columns):
    """Execute nvidia-smi command and parse output."""
    proc = subprocess.Popen(
        (
            "nvidia-smi",
            "--query-{}={}".format(query, ",".join(columns)),
            "--format=csv,noheader,nounits",
        ),
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    return (dict(zip(columns, line.strip().split(", "))) for line in proc.stdout)


def getent_password():
    """Fetch system user information."""
    passwd = subprocess.Popen(("getent", "passwd"), stdout=subprocess.PIPE)
    users = dict()
    for line in passwd.stdout:
        line = line.strip().split(b":")
        users[int(line[2])] = line[0].decode()
    return users


def collect_gpu_data():
    """Collect GPU usage data."""
    users = getent_password()
    processes = dict()
    apps_by_gpu = defaultdict(list)
    memory_usage = defaultdict(int)

    # Collect GPU utilization and memory information
    gpus = tuple(
        nvidia_smi(
            "gpu",
            ("gpu_uuid", "index", "memory.used", "memory.total", "utilization.gpu"),
        )
    )

    # Collect process-specific GPU usage data
    apps = nvidia_smi("compute-apps", ("gpu_uuid", "pid", "name", "used_memory"))
    for app in apps:
        app["pid"] = int(app["pid"])
        if app["pid"] not in processes:
            try:
                with open("/proc/{:d}/loginuid".format(app["pid"])) as f:
                    processes[app["pid"]] = {"uid": int(next(f).strip())}
            except FileNotFoundError:
                processes[app["pid"]] = dict()
        app["used_memory"] = int(app["used_memory"])
        apps_by_gpu[app["gpu_uuid"]].append(app)
        if "uid" in processes[app["pid"]]:
            memory_usage[processes[app["pid"]]["uid"]] += app["used_memory"]

    return gpus, apps_by_gpu, memory_usage, processes, users


def update_metrics():
    """Update Prometheus metrics."""
    gpus, apps_by_gpu, memory_usage, processes, users = collect_gpu_data()

    # Update GPU utilization and memory usage metrics
    for gpu in gpus:
        gpu["index"] = int(gpu["index"])
        gpu["memory.used"] = int(gpu["memory.used"])
        gpu["memory.total"] = int(gpu["memory.total"])
        gpu["utilization.gpu"] = int(gpu["utilization.gpu"])

        gpu_memory_usage_gauge.labels(
            gpu_index=gpu["index"], gpu_uuid=gpu["gpu_uuid"]
        ).set(gpu["memory.used"])

        gpu_utilization_gauge.labels(
            gpu_index=gpu["index"], gpu_uuid=gpu["gpu_uuid"]
        ).set(gpu["utilization.gpu"])

        # Calculate per-process GPU utilization
        total_gpu_memory = gpu["memory.total"]
        for app in apps_by_gpu[gpu["gpu_uuid"]]:
            if "uid" in processes[app["pid"]]:
                user = users.get(processes[app["pid"]]["uid"], "[Unknown]")
            else:
                user = "[Not Found]"

            gpu_process_memory_usage_gauge.labels(
                pid=app["pid"],
                user=user,
                gpu_index=gpu["index"],
                process_name=app["name"],
            ).set(app["used_memory"])

            # Estimate process GPU utilization
            if total_gpu_memory > 0:
                estimated_utilization = (app["used_memory"] / total_gpu_memory) * gpu[
                    "utilization.gpu"
                ]
                gpu_process_utilization_gauge.labels(
                    pid=app["pid"],
                    user=user,
                    gpu_index=gpu["index"],
                    process_name=app["name"],
                ).set(estimated_utilization)


if __name__ == "__main__":
    # Parse arguments and environment variables
    parser = argparse.ArgumentParser(description="GPU Exporter for Prometheus")
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("METRIC_SCRAPE_INTERVAL", 10)),
        help="Metric scrape interval in seconds (default: 10 seconds)",
    )
    args = parser.parse_args()

    scrape_interval = args.interval

    # Start Prometheus HTTP server
    start_http_server(8000)  # Port 8000
    print(
        f"Exporter is running on port 8000 with a scrape interval of {scrape_interval} seconds."
    )
    while True:
        update_metrics()
        time.sleep(scrape_interval)
