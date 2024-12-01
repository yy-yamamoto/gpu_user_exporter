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
gpu_utilization_gauge = Gauge(
    "gpu_utilization", "GPU Utilization (%)", ["gpu_index", "gpu_uuid"]
)
gpu_user_memory_usage_gauge = Gauge(
    "gpu_user_memory_usage", "User Memory Usage (MiB)", ["gpu_index", "user"]
)
gpu_user_utilization_gauge = Gauge(
    "gpu_user_utilization", "User GPU Utilization (%)", ["gpu_index", "user"]
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
    user_memory_usage = defaultdict(
        lambda: defaultdict(int)
    )  # {gpu_index: {user: memory}}
    user_utilization = defaultdict(
        lambda: defaultdict(float)
    )  # {gpu_index: {user: utilization}}
    gpu_data = {}
    active_users = set()

    # Collect GPU utilization and memory information
    gpus = tuple(
        nvidia_smi(
            "gpu",
            ("gpu_uuid", "index", "memory.used", "memory.total", "utilization.gpu"),
        )
    )

    # Collect process-specific GPU usage data
    apps = nvidia_smi("compute-apps", ("gpu_uuid", "pid", "used_memory"))

    for app in apps:
        app["used_memory"] = int(app["used_memory"])
        gpu_uuid = app["gpu_uuid"]

        try:
            with open(f"/proc/{app['pid']}/loginuid") as f:
                uid = int(f.read().strip())
                user = users.get(uid, "[Unknown]")
        except FileNotFoundError:
            user = "[Unknown]"

        # Aggregate memory usage by user and GPU
        for gpu in gpus:
            if gpu["gpu_uuid"] == gpu_uuid:
                gpu_index = int(gpu["index"])
                user_memory_usage[gpu_index][user] += app["used_memory"]
                active_users.add((gpu_index, user))

    # Calculate user utilization
    for gpu in gpus:
        gpu_index = int(gpu["index"])
        total_gpu_memory = int(gpu["memory.total"])
        gpu_utilization_value = int(gpu["utilization.gpu"])

        total_memory_used = sum(user_memory_usage[gpu_index].values())
        if total_gpu_memory > 0 and total_memory_used > 0:
            for user, memory_used in user_memory_usage[gpu_index].items():
                # Calculate the user's share of GPU utilization
                user_utilization[gpu_index][user] = (
                    memory_used / total_memory_used
                ) * gpu_utilization_value
        else:
            for user in user_memory_usage[gpu_index].keys():
                user_utilization[gpu_index][user] = 0.0

    # Prepare GPU data for Prometheus metrics
    for gpu in gpus:
        gpu["index"] = int(gpu["index"])
        gpu["memory.used"] = int(gpu["memory.used"])
        gpu["memory.total"] = int(gpu["memory.total"])
        gpu["utilization.gpu"] = int(gpu["utilization.gpu"])

        gpu_data[gpu["index"]] = {
            "gpu_uuid": gpu["gpu_uuid"],
            "memory_used": gpu["memory.used"],
            "utilization": gpu["utilization.gpu"],
            "total_memory": gpu["memory.total"],
        }

    return gpu_data, user_memory_usage, user_utilization, active_users


def update_metrics(previous_user_stats, grace_period):
    """Update Prometheus metrics."""
    (
        gpu_data,
        user_memory_usage,
        user_utilization,
        active_users,
    ) = collect_gpu_data()

    current_time = time.time()

    # Update GPU utilization and memory usage metrics
    for gpu_index, gpu in gpu_data.items():
        gpu_memory_usage_gauge.labels(
            gpu_index=gpu_index, gpu_uuid=gpu["gpu_uuid"]
        ).set(gpu["memory_used"])

        gpu_utilization_gauge.labels(gpu_index=gpu_index, gpu_uuid=gpu["gpu_uuid"]).set(
            gpu["utilization"]
        )

    # Update per-user metrics and handle inactive users
    for gpu_index, user_data in user_memory_usage.items():
        for user, memory_used in user_data.items():
            utilization = user_utilization[gpu_index][user]

            gpu_user_memory_usage_gauge.labels(gpu_index=gpu_index, user=user).set(
                memory_used
            )
            gpu_user_utilization_gauge.labels(gpu_index=gpu_index, user=user).set(
                utilization
            )

            # Update last_seen for active users
            previous_user_stats[(gpu_index, user)] = {"last_seen": current_time}

    for (gpu_index, user), stats in list(previous_user_stats.items()):
        if (gpu_index, user) not in active_users:
            # Set metrics to zero for inactive users
            gpu_user_memory_usage_gauge.labels(gpu_index=gpu_index, user=user).set(0)
            gpu_user_utilization_gauge.labels(gpu_index=gpu_index, user=user).set(0.0)

            # Check if metrics should be removed
            elapsed_time = current_time - stats["last_seen"]
            if elapsed_time >= grace_period:
                gpu_user_memory_usage_gauge.remove(gpu_index=gpu_index, user=user)
                gpu_user_utilization_gauge.remove(gpu_index=gpu_index, user=user)
                del previous_user_stats[(gpu_index, user)]

    return


if __name__ == "__main__":
    # Parse arguments and environment variables
    parser = argparse.ArgumentParser(description="GPU Exporter for Prometheus")
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("METRIC_SCRAPE_INTERVAL", 5)),
        help="Metric scrape interval in seconds (default: 5 seconds)",
    )
    parser.add_argument(
        "--grace-period",
        type=int,
        default=30,
        help="Time (in seconds) to keep 0 values before removing metrics (default: 30 seconds)",
    )
    args = parser.parse_args()

    scrape_interval = args.interval
    grace_period = args.grace_period

    # Start Prometheus HTTP server
    start_http_server(8000)  # Port 8000
    print(
        f"Exporter is running on port 8000 with a scrape interval of {scrape_interval} seconds and a grace period of {grace_period} seconds."
    )

    # Track previous user memory and utilization stats
    previous_user_stats = {}

    while True:
        update_metrics(previous_user_stats, grace_period)
        time.sleep(scrape_interval)
