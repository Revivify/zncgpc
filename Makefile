# Makefile for ZNC GCP Deployment Helper

.PHONY: help install deploy clean-pyc

# Default target: Show help
default: help

help:
	@echo "Makefile for ZNC GCP Deployment Helper"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  help          Show this help message."
	@echo "  install       Install Python dependencies from requirements.txt."
	@echo "  deploy        Show an example command to run the deployment script."
	@echo "                (You will need to replace placeholders like YOUR_PROJECT_ID)."
	@echo "  clean-pyc     Remove Python bytecode files."
	@echo ""

install:
	@echo "Installing Python dependencies from requirements.txt..."
	pip install -r requirements.txt
	@echo "Installation complete."

deploy:
	@echo "Example command to deploy ZNC:"
	@echo "python deploy_znc.py \\"
	@echo "    --project-id YOUR_PROJECT_ID \\"
	@echo "    --zone us-central1-c \\"
	@echo "    --instance-name znc-bouncer-py \\"
	@echo "    --static-ip-name znc-static-ip \\"
	@echo "    --region us-central1 \\"
	@echo "    --znc-port 6697"
	@echo ""
	@echo "NOTE: Replace YOUR_PROJECT_ID and adjust other parameters as needed."

clean-pyc:
	@echo "Cleaning Python bytecode files..."
	find . -name "*.pyc" -exec rm -f {} +
	find . -name "*.pyo" -exec rm -f {} +
	find . -name "*~" -exec rm -f {} +
	find . -name "__pycache__" -exec rm -rf {} +
	@echo "Cleanup complete."
