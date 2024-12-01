# Makefile for installing and managing the GPU User Exporter

# Variables
INSTALL_DIR=/opt/gpu_user_exporter
SERVICE_FILE=/etc/systemd/system/gpu_user_exporter.service
LOCAL_SERVICE_FILE=gpu_user_exporter.service
PYTHON=python3
SCRIPT=gpu_user_exporter.py
DEFAULT_INTERVAL=10
DEFAULT_GRACE_PERIOD=60

# Commands
.PHONY: all install clean uninstall enable disable

all: install

install:
	@echo "Installing GPU User Exporter..."
	# Create installation directory
	sudo mkdir -p $(INSTALL_DIR)
	# Copy the script to the installation directory
	sudo cp $(SCRIPT) $(INSTALL_DIR)/
	sudo chmod +x $(INSTALL_DIR)/$(SCRIPT)
	# Create virtual environment and install dependencies
	sudo $(PYTHON) -m venv $(INSTALL_DIR)/venv
	sudo $(INSTALL_DIR)/venv/bin/pip install --upgrade pip
	sudo $(INSTALL_DIR)/venv/bin/pip install -r requirements.txt

	# Copy the service file from the current directory
	@echo "Installing systemd service file..."
	sudo cp $(LOCAL_SERVICE_FILE) $(SERVICE_FILE)
	# Adjust systemd service file to use virtual environment
	sudo sed -i 's|ExecStart=.*|ExecStart=$(INSTALL_DIR)/venv/bin/python $(INSTALL_DIR)/$(SCRIPT) --interval $(DEFAULT_INTERVAL) --grace-period $(DEFAULT_GRACE_PERIOD)|' $(SERVICE_FILE)

	# Reload systemd and enable the service
	@echo "Enabling GPU User Exporter service..."
	sudo systemctl daemon-reload
	sudo systemctl enable $(LOCAL_SERVICE_FILE)
	sudo systemctl start $(LOCAL_SERVICE_FILE)
	@echo "GPU User Exporter installed and running."

clean:
	@echo "Cleaning up installation..."
	# Stop the service if running
	-sudo systemctl stop $(LOCAL_SERVICE_FILE)
	# Remove the installation directory
	-sudo rm -rf $(INSTALL_DIR)
	# Remove the systemd service file
	-sudo rm -f $(SERVICE_FILE)
	# Reload systemd
	-sudo systemctl daemon-reload
	@echo "Cleaned up GPU User Exporter installation."

uninstall: clean

enable:
	@echo "Enabling GPU User Exporter service..."
	sudo systemctl enable $(LOCAL_SERVICE_FILE)
	sudo systemctl start $(LOCAL_SERVICE_FILE)
	@echo "GPU User Exporter service enabled."

disable:
	@echo "Disabling GPU User Exporter service..."
	sudo systemctl disable $(LOCAL_SERVICE_FILE)
	sudo systemctl stop $(LOCAL_SERVICE_FILE)
	@echo "GPU User Exporter service disabled."
