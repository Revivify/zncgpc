# ZNC Deployment on GCP

This project provides Python scripts to automate the deployment of a ZNC IRC bouncer on a Google Cloud Platform (GCP) Compute Engine virtual machine.
It leverages the `google-cloud-compute` Python library to interact with GCP.
The deployment aims to follow the guidance in `plan.md` for a cost-effective setup, targeting the GCP Free Tier where possible for key components.

# Prerequisites

*   **Python:** Version 3.8 or higher.
*   **pip:** Python package installer (usually comes with Python).
*   **Google Cloud SDK:** The `gcloud` command-line interface must be installed and initialized.
    *   Follow the [official installation guide](https://cloud.google.com/sdk/docs/install).
    *   Initialize the SDK: `gcloud init`.
*   **GCP Project:** A Google Cloud Project with Billing enabled.
*   **Permissions:** Ensure the user account or service account used for authentication has the necessary IAM roles. Minimally, this includes:
    *   `Compute Admin` (or `roles/compute.admin`) for creating and managing VMs, disks, static IPs, and firewalls.
    *   `Service Account User` (or `roles/iam.serviceAccountUser`) if the VM will run under a specific service account (though this script uses the default Compute Engine service account).

#### Installing Dependencies
This project uses a `requirements.txt` file to manage Python dependencies. To install them, run:
```bash
pip install -r requirements.txt
```
This will install `google-cloud-compute` and `google-api-python-client`.

*   **Authenticate for Application Default Credentials (ADC):**
    The Python script uses ADC to authenticate.
    ```bash
    gcloud auth application-default login
    ```

# Included Files

*   `deploy_znc.py`: The main Python script for deploying and managing GCP resources for the ZNC VM.
*   `undeploy_znc.py`: The Python script for deprovisioning/deleting the ZNC GCP resources.
*   `startup-script.sh`: A shell script that is executed on the VM's first boot. It handles installing ZNC, creating a dedicated user, and setting up ZNC as a systemd service.
*   `requirements.txt`: Lists the Python dependencies required for the project.
*   `Makefile`: Provides convenient targets for common operations like installing dependencies and cleaning the project.
*   `plan.md`: The original planning document outlining the intended architecture and deployment strategy.
*   `README.md`: This file, providing documentation for the project.

# Using the Makefile

A `Makefile` is provided to simplify common operations. Here are the available targets:

*   `make help`: Displays a help message with all available targets. This is also the default target if you just run `make`.
*   `make install`: Installs all necessary Python dependencies from `requirements.txt` using pip.
*   `make deploy`: Shows an example command to run the `deploy_znc.py` script. You will need to replace placeholder values like `YOUR_PROJECT_ID` in the example command. This target does not execute the deployment but prints the command for your convenience.
*   `make clean-pyc`: Removes Python bytecode files (`.pyc`, `.pyo`), editor backup files (`*~`), and `__pycache__` directories from the project.

To run a target, simply type `make <target_name>` in your terminal from the project's root directory. For example:
```bash
make install
```

# Deployment Steps

1.  **Clone the repository / Download the scripts:**
    Obtain all the files (`deploy_znc.py`, `startup-script.sh`, `plan.md`, `README.md`) and place them in a local directory.

2.  **Review Configuration:**
    *   Open `deploy_znc.py` in a text editor to familiarize yourself with the available command-line arguments and their default values.
    *   Alternatively, run `python deploy_znc.py --help` to see all options.
    *   The most critical argument you **must** provide is `--project-id YOUR_PROJECT_ID`.

3.  **Execute the script:**
    Navigate to the directory containing the scripts in your terminal and run the deployment script.
    A minimal execution command is:
    ```bash
    python deploy_znc.py --project-id YOUR_PROJECT_ID --zone us-west1-a
    ```
    Replace `YOUR_PROJECT_ID` with your actual Google Cloud Project ID.

4.  **Command-Line Arguments:**
    The script offers several arguments to customize the deployment. Here are some key ones:
    *   `--project-id`: **Required.** Your Google Cloud Project ID.
    *   `--zone`: The GCP zone for the VM (e.g., `us-central1-c`). Default: `us-west1-a`.
    *   `--instance-name`: Name for the VM. Default: `znc-bouncer-vm`.
    *   `--static-ip-name`: If provided, a static IP with this name will be reserved/used. This incurs a small cost. If omitted, an ephemeral IP is used.
    *   `--region`: Region for the static IP if `--static-ip-name` is used. Defaults to the region of the `--zone`.
    *   `--znc-port`: The port ZNC will listen on, and which the firewall will open. Default: `6697`.
    *   `--network-tag`: Network tag for the VM and firewall rule. Default: `znc-bouncer-node`.
    *   `--firewall-rule-name`: Name for the firewall rule. Default: `allow-znc-access`.
    *   For a full list of arguments, their descriptions, and default values, run:
        ```bash
        python deploy_znc.py --help
        ```

5.  **Example Usage:**
    *   **Basic deployment** (ephemeral IP, default names, in `us-central1-c`):
        ```bash
        python deploy_znc.py --project-id my-gcp-project --zone us-central1-c
        ```
    *   **Deployment with a static IP** (named `znc-static-ip` in region `us-central1`):
        ```bash
        python deploy_znc.py --project-id my-gcp-project --zone us-central1-c --static-ip-name znc-static-ip --region us-central1
        ```
    *   **Specifying a custom ZNC port** (e.g., 7000):
        ```bash
        python deploy_znc.py --project-id my-gcp-project --zone us-central1-c --znc-port 7000
        ```

# Post-Deployment Configuration (IMPORTANT)

The `deploy_znc.py` script provisions the infrastructure and the `startup-script.sh` installs ZNC. However, the **initial ZNC user and network configuration must be done manually inside the VM.**

1.  **SSH into the VM:**
    *   Use the `gcloud` command:
        ```bash
        gcloud compute ssh YOUR_INSTANCE_NAME --project YOUR_PROJECT_ID --zone YOUR_ZONE
        ```
    *   Example (using default instance name):
        ```bash
        gcloud compute ssh znc-bouncer-vm --project my-gcp-project --zone us-central1-c
        ```

2.  **Initial ZNC Setup:**
    *   The `startup-script.sh` creates a system user `zncuser` to run ZNC.
    *   Switch to this user:
        ```bash
        sudo su - zncuser
        ```
    *   Run the ZNC configuration utility:
        ```bash
        znc --makeconf
        ```
    *   Follow the on-screen prompts. Key considerations:
        *   **Listen Port:** Ensure this matches the port you specified with `--znc-port` during deployment (default is `6697`).
        *   **SSL/TLS:** Recommended for secure connections. ZNC can generate a self-signed certificate, or you can provide your own.
        *   **User:** Create your first ZNC user (this is different from the `zncuser` system user).
        *   **Networks:** Configure the IRC networks you want ZNC to connect to.
        *   When asked "Launch ZNC now?", you can choose yes.

3.  **Verify ZNC Service:**
    *   The `startup-script.sh` enables and starts the `znc.service`.
    *   If you chose not to launch ZNC via `znc --makeconf` or want to check its status:
        ```bash
        sudo systemctl status znc.service
        ```
    *   To start or restart it if needed:
        ```bash
        sudo systemctl start znc.service
        # or
        sudo systemctl restart znc.service
        ```

4.  **Check Logs:**
    *   **Startup Script Logs (on the VM):** For issues during the automated setup:
        ```bash
        cat /var/log/startup-script.log
        ```
    *   **ZNC Logs (on the VM):** ZNC's own logs are typically located within the `zncuser`'s home directory, under `.znc`. The exact path depends on your configuration during `znc --makeconf` (e.g., `/home/zncuser/.znc/users/YOUR_ZNC_USER/moddata/log/...`).

# Cost Considerations

*   **VM Instance:** The default `e2-micro` machine type is part of the GCP Free Tier (one instance per month in eligible US regions: `us-west1`, `us-central1`, `us-east1`, subject to change). Using other regions, different machine types, or more than one `e2-micro` instance will incur costs.
*   **Persistent Disk:** The default 10GB `pd-balanced` disk is within the 30GB Free Tier limit for standard persistent disk storage. Larger disks or SSDs will cost more.
*   **Static IP Address:** If you use the `--static-ip-name` argument, a static IP address is reserved.
    *   Attached to a running VM: Incurs a small hourly cost (approx. $2-3/month).
    *   Unattached or attached to a stopped VM: Incurs a higher hourly cost.
    *   Using an ephemeral IP (default behavior, by omitting `--static-ip-name`) has no direct additional cost but the IP address will change if the VM is stopped and started.
*   **Data Egress:** GCP provides 1GB of free network egress per month (to regions outside GCP, excluding China and Australia). ZNC usage is typically very low and should easily stay within this limit.
*   **Always check the official documentation for the latest pricing and Free Tier details:**
    *   [GCP Free Tier Documentation](https://cloud.google.com/free/docs/gcp-free-tier)
    *   [Compute Engine Pricing](https://cloud.google.com/compute/all-pricing)

# Undeploying Resources (Cleanup)

To avoid ongoing charges for unused resources, especially the VM instance and any reserved static IP address, it's important to delete them when they are no longer needed. The `undeploy_znc.py` script is provided to automate this process.

The script will attempt to delete:
1.  The ZNC VM instance.
2.  The static IP address (if a `--static-ip-name` was specified during deployment and is provided to the undeploy script).
3.  The firewall rule associated with ZNC access.

## Command-Line Usage

```bash
python undeploy_znc.py --project-id YOUR_PROJECT_ID --zone YOUR_ZONE [OPTIONS]
```

### Arguments:

*   `--project-id YOUR_PROJECT_ID`: **(Required)** Your Google Cloud project ID.
*   `--zone YOUR_ZONE`: **(Required)** The GCP zone where the VM instance was created (e.g., `us-central1-c`).
*   `--instance-name NAME`: Name of the VM instance to delete. Defaults to `znc-bouncer-vm`.
*   `--static-ip-name NAME`: Name of the static IP address to delete. If you reserved a static IP during deployment, you must provide its name here to delete it. If omitted, static IP deletion is skipped.
*   `--region REGION`: Region of the static IP address. Required if `--static-ip-name` is provided. If not specified, the script will attempt to derive it from the `--zone` argument.
*   `--firewall-rule-name NAME`: Name of the firewall rule to delete. Defaults to `allow-znc-access` (this should match the default used by `deploy_znc.py`).
*   `--yes`: A boolean flag (include as `--yes`) to bypass the interactive confirmation prompt and proceed directly with deletions.

### Example Command:

```bash
python undeploy_znc.py \
    --project-id my-gcp-project \
    --zone us-central1-c \
    --instance-name znc-bouncer-vm \
    --static-ip-name znc-static-ip \
    --firewall-rule-name allow-znc-access
```
Adjust the parameters to match the resources you deployed. If you did not use a static IP, omit the `--static-ip-name` and `--region` arguments.

### Confirmation Prompt

By default, the `undeploy_znc.py` script will list the resources it plans to delete and ask for your confirmation before proceeding. To bypass this prompt (e.g., in automated environments), you can use the `--yes` flag.

**Important:** Always double-check the parameters to ensure you are deleting the correct resources. Deletion is irreversible.

# TODO / Future Enhancements

*   Add a deprovisioning feature/flag to `deploy_znc.py` to automate resource cleanup.
*   Explore options for non-interactive ZNC initial configuration (e.g., by uploading a pre-generated `znc.conf` file via metadata or other means and having the startup script place it).
*   Implement more robust checking of existing firewall rule configurations.
*   Add support for specifying a custom service account for the VM.
