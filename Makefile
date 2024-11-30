# Makefile for installing and managing the GPU Exporter

# Variables
INSTALL_DIR=/opt/gpu_exporter
SERVICE_FILE=/etc/systemd/system/gpu_exporter.service
LOCAL_SERVICE_FILE=gpu_exporter.service
PYTHON=python3
SCRIPT=gpu_exporter.py

# Commands
.PHONY: all install clean uninstall enable disable

all: install

install:
	@echo "Installing GPU Exporter..."
	# Create installation directory
	sudo mkdir -p $(INSTALL_DIR)
	# Copy the script to the installation directory
	sudo cp $(SCRIPT) $(INSTALL_DIR)/
	sudo chmod +x $(INSTALL_DIR)/$(SCRIPT)
	# Install Python dependencies
	sudo $(PYTHON) -m pip install --upgrade pip
	sudo $(PYTHON) -m pip install -r requirements.txt

	# Copy the service file from the current directory
	@echo "Installing systemd service file..."
	sudo cp $(LOCAL_SERVICE_FILE) $(SERVICE_FILE)

	# Reload systemd and enable the service
	@echo "Enabling GPU Exporter service..."
	sudo systemctl daemon-reload
	sudo systemctl enable gpu_exporter.service
	sudo systemctl start gpu_exporter.service
	@echo "GPU Exporter installed and running."

clean:
	@echo "Cleaning up installation..."
	# Stop the service if running
	-sudo systemctl stop gpu_exporter.service
	# Remove the installation directory
	-sudo rm -rf $(INSTALL_DIR)
	# Remove the systemd service file
	-sudo rm -f $(SERVICE_FILE)
	# Reload systemd
	-sudo systemctl daemon-reload
	@echo "Cleaned up GPU Exporter installation."

uninstall: clean

enable:
	@echo "Enabling GPU Exporter service..."
	sudo systemctl enable gpu_exporter.service
	sudo systemctl start gpu_exporter.service
	@echo "GPU Exporter service enabled."

disable:
	@echo "Disabling GPU Exporter service..."
	sudo systemctl disable gpu_exporter.service
	sudo systemctl stop gpu_exporter.service
	@echo "GPU Exporter service disabled."
