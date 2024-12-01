# GPU User Exporter

GPU User Exporter is a tool designed to monitor and export GPU usage metrics for users. This tool helps in tracking GPU utilization and provides insights for optimizing resource allocation.

This is a Python-based tool that collects GPU usage data, including memory usage, utilization rates, and process-level metrics, and exposes them to Prometheus. It helps you monitor GPU performance and visualize it using tools like Grafana.


## Features

- Collects GPU memory usage and utilization rates
- Provides per-process GPU usage metrics (memory and utilization)
- Compatible with Prometheus for monitoring
- Supports `systemd` for automatic startup

## Requirements

- **Operating System**: Linux
- **Python**: 3.6 or higher
- **NVIDIA Driver**: Environment with `nvidia-smi` available
- **Prometheus**: For data collection
- **pip**: For installing Python dependencies
- **venv**: For creating a virtual environment

## Installation

### 1. Clone the repository

```shell
git clone https://your-repository-url/gpu_exporter.git
cd gpu_exporter
```

### 3. Use the `Makefile` for installation

Run the following command to install the exporter and set up the service:

```shell
make install
```

## Usage

### Managing the Service

1. **Enable the service to start on boot:**

    ```shell
    sudo systemctl enable gpu_exporter.service
    ```

1. **Start the service manually:**

    ```shell
    sudo systemctl start gpu_exporter.service
    ```

1. **Check the service status:**

    ```shell
    sudo systemctl status gpu_exporter.service
    ```

1. **Stop the service:**

    ```shell
    sudo systemctl stop gpu_exporter.service
    ```

1. **Disable the service:**

    ```shell
    sudo systemctl disable gpu_exporter.service
    ```

## Metrics

The GPU Exporter exposes the following metrics:

1. **Overall GPU Metrics**
    - `gpu_memory_usage`: Memory usage of each GPU in MiB
    - `gpu_utilization`: Utilization rate of each GPU in %

1. **Per-User Metrics**
    - `gpu_user_memory_usage`: Memory usage per user in MiB

### Example Metrics

Below is an example of metrics exposed to Prometheus:


    # HELP gpu_memory_usage GPU Memory Usage (MiB)
    # TYPE gpu_memory_usage gauge
    gpu_memory_usage{gpu_index="0", gpu_uuid="GPU-abc123"} 2048.0

    # HELP gpu_utilization GPU Utilization (%)
    # TYPE gpu_utilization gauge
    gpu_utilization{gpu_index="0", gpu_uuid="GPU-abc123"} 75.0

    # HELP gpu_process_memory_usage Process Memory Usage (MiB)
    # TYPE gpu_process_memory_usage gauge
    gpu_process_memory_usage{user="john", gpu_index="0"} 512.0

## Uninstallation

To remove the installed service and script, run the following command:

```shell
make uninstall
```

## Troubleshooting

1. **`Permission denied` error**

    If you encounter a `Permission denied` error when creating or writing to `/opt`, run the following commands:

    ```shell
    sudo mkdir -p /opt/gpu_exporter
    sudo chown -R $(whoami):$(whoami) /opt/gpu_exporter
    ```

1. **Prometheus cannot scrape data**

    Check if the exporter is running:

    ```shell
    curl http://localhost:8000
    ```

## License

This project is licensed under the MIT License.
