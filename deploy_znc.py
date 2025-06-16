from google.api_core.exceptions import NotFound
import google.cloud.compute_v1 as compute_v1
import argparse
import time
import sys # For sys.exit

# ##################################
# # Static IP Address Management #
# ##################################

def reserve_static_ip(project_id: str, region: str, address_name: str) -> compute_v1.Address | None:
    """
    Reserves a new static external IP address or gets an existing one.

    Args:
        project_id: The ID of the Google Cloud project.
        region: The region to reserve the IP address in (e.g., "us-west1").
        address_name: The desired name for the static IP address.

    Returns:
        The compute_v1.Address object if successful, None otherwise.
    """
    address_client = compute_v1.AddressesClient()
    address_resource = compute_v1.Address(name=address_name) # Specify the desired name

    try:
        # Check if the address already exists
        try:
            existing_address = address_client.get(project=project_id, region=region, address=address_name)
            print(f"INFO: Static IP address '{address_name}' already exists in region {region}: {existing_address.address}")
            return existing_address
        except NotFound:
            print(f"INFO: Static IP address '{address_name}' not found in region {region}. Attempting to create...")
        except Exception as e: # Catch other potential errors during get
            print(f"WARNING: Error checking for existing IP address '{address_name}': {e}. Will attempt creation.")


        print(f"ACTION: Reserving static IP address '{address_name}' in project '{project_id}', region '{region}'...")
        operation = address_client.insert(project=project_id, region=region, address_resource=address_resource)

        # Wait for the regional operation to complete
        op_start_time = time.time()
        region_operation_client = compute_v1.RegionOperationsClient()
        while operation.status != compute_v1.Operation.Status.DONE:
            time.sleep(5) # Increased sleep time
            operation = region_operation_client.get(project=project_id, region=region, operation=operation.name)
            elapsed_time = time.time() - op_start_time
            print(f"INFO: Waiting for IP reservation operation to complete... Status: {operation.status.name} (Elapsed: {elapsed_time:.0f}s)")
            if elapsed_time > 300: # 5 minutes timeout
                print(f"ERROR: Timeout waiting for IP reservation operation for '{address_name}'.")
                return None


        if operation.error:
            print(f"ERROR: Could not reserve static IP address '{address_name}'. Error: {operation.error.errors}")
            return None

        reserved_address = address_client.get(project=project_id, region=region, address=address_name)
        print(f"SUCCESS: Static IP address '{address_name}' reserved successfully: {reserved_address.address}")
        return reserved_address
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while reserving or getting static IP '{address_name}': {e}")
        return None

# ##################################
# # Firewall Rule Management     #
# ##################################

def create_firewall_rule(project_id: str, firewall_rule_name: str, network_name: str,
                         target_tag: str, allowed_ports: list[str]) -> bool:
    """
    Creates a new firewall rule or confirms if an existing one matches the configuration.

    Args:
        project_id: The ID of the Google Cloud project.
        firewall_rule_name: The name for the firewall rule.
        network_name: The network URI (e.g., "global/networks/default").
        target_tag: The network tag the rule applies to.
        allowed_ports: A list of strings specifying protocols and ports (e.g., ["tcp:6697"]).

    Returns:
        True if the rule is successfully created or already exists and matches, False otherwise.
    """
    firewall_client = compute_v1.FirewallsClient()

    # Define the 'allowed' part of the firewall rule
    allowed_config = [
        compute_v1.Allowed(
            i_p_protocol=port_protocol.split(":")[0].lower(), # Ensure protocol is lowercase (tcp, udp, icmp, etc.)
            ports=[port_protocol.split(":")[1]]
        ) for port_protocol in allowed_ports
    ]

    firewall_resource = compute_v1.Firewall(
        name=firewall_rule_name,
        network=network_name,
        source_ranges=["0.0.0.0/0"],  # Allow traffic from any source
        target_tags=[target_tag],
        allowed=allowed_config,
        description="Firewall rule for ZNC bouncer access, created by deploy_znc.py script."
    )

    try:
        # Check if the firewall rule already exists
        try:
            existing_firewall = firewall_client.get(project=project_id, firewall=firewall_rule_name)
            if existing_firewall:
                # Basic check: if it exists and applies to the same tag and ports (more complex checks can be added)
                # This is a simplistic check. A robust check would compare all fields.
                existing_allowed_simple = [f"{a.i_p_protocol}:{a.ports[0]}" for a in existing_firewall.allowed]
                if existing_firewall.target_tags == [target_tag] and sorted(existing_allowed_simple) == sorted(allowed_ports):
                    print(f"INFO: Firewall rule '{firewall_rule_name}' already exists and matches target tag and ports.")
                    return True
                else:
                    print(f"WARNING: Firewall rule '{firewall_rule_name}' already exists but has different configuration. Manual review recommended.")
                    # Not returning False, as it exists. User might need to delete/update it.
                    return True # Or False, depending on desired behavior for mismatches
        except NotFound:
            print(f"INFO: Firewall rule '{firewall_rule_name}' not found. Attempting to create...")
        except Exception as e:
            print(f"WARNING: Error checking for existing firewall rule '{firewall_rule_name}': {e}. Will attempt creation.")


        print(f"ACTION: Creating firewall rule '{firewall_rule_name}' in project '{project_id}' for target tag '{target_tag}' on network '{network_name}' allowing ports {allowed_ports}...")
        operation = firewall_client.insert(project=project_id, firewall_resource=firewall_resource)

        op_start_time = time.time()
        global_operation_client = compute_v1.GlobalOperationsClient() # Use specific client for global ops
        while operation.status != compute_v1.Operation.Status.DONE:
            time.sleep(5)
            # For global operations, use the GlobalOperationsClient
            operation = global_operation_client.get(project=project_id, operation=operation.name)
            elapsed_time = time.time() - op_start_time
            print(f"INFO: Waiting for firewall rule creation operation to complete... Status: {operation.status.name} (Elapsed: {elapsed_time:.0f}s)")
            if elapsed_time > 300: # 5 minutes timeout
                 print(f"ERROR: Timeout waiting for firewall rule creation for '{firewall_rule_name}'.")
                 return False

        if operation.error:
            print(f"ERROR: Could not create firewall rule '{firewall_rule_name}'. Error: {operation.error.errors}")
            return False

        print(f"SUCCESS: Firewall rule '{firewall_rule_name}' created successfully.")
        return True
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while creating or checking firewall rule '{firewall_rule_name}': {e}")
        return False

# ##################################
# # VM Instance Management       #
# ##################################

def create_vm_instance(project_id: str, zone: str, instance_name: str,
                       machine_type: str, image_project: str, image_family: str,
                       disk_size_gb: int, disk_type: str, assign_ephemeral_ip: bool = True,
                       tags: list[str] | None = None,
                       startup_script_content: str | None = None) -> bool:
    """
    Creates a new VM instance in the specified project and zone.

    Args:
        project_id: The ID of the Google Cloud project.
        zone: The zone to create the instance in (e.g., "us-west1-a").
        instance_name: The name for the new VM instance.
        machine_type: The machine type (e.g., "e2-micro").
        image_project: The project ID for the boot image (e.g., "debian-cloud").
        image_family: The image family for the boot image (e.g., "debian-11").
        disk_size_gb: The size of the boot disk in GB.
        disk_type: The type of the boot disk (e.g., "pd-standard", "pd-balanced", "pd-ssd").
        assign_ephemeral_ip: If True, assigns an ephemeral public IP. Set to False if using a static IP.
        tags: A list of network tags to apply to the instance.
        startup_script_content: String content of the startup script to be run on first boot.

    Returns:
        True if the instance is created successfully, False otherwise.
    """
    instance_client = compute_v1.InstancesClient()

    # Construct the machine type URI
    machine_type_uri = f"zones/{zone}/machineTypes/{machine_type}"

    # Configure the boot disk
    boot_disk = compute_v1.AttachedDisk(
        boot=True,
        auto_delete=True, # Delete the disk when the instance is deleted
        type_="PERSISTENT", # Changed to string representation
        initialize_params=compute_v1.AttachedDiskInitializeParams(
            source_image=f"projects/{image_project}/global/images/family/{image_family}",
            disk_size_gb=disk_size_gb,
            disk_type=f"zones/{zone}/diskTypes/{disk_type}",
        ),
    )

    # Configure the network interface
    network_interface = compute_v1.NetworkInterface(name="global/networks/default") # Use the default VPC network
    if assign_ephemeral_ip:
        network_interface.access_configs = [
            compute_v1.AccessConfig(
                name="External NAT", # Standard name for ephemeral IP config
                network_tier="STANDARD", # Or PREMIUM, depending on needs
                type_="ONE_TO_ONE_NAT"
            )
        ]
    # If not assigning ephemeral IP, access_configs list remains empty initially.
    # It will be populated by assign_static_ip_to_vm if a static IP is used.

    # Prepare the instance resource
    instance_resource = compute_v1.Instance(
        name=instance_name,
        machine_type=machine_type_uri,
        disks=[boot_disk],
        network_interfaces=[network_interface]
    )

    # Add tags if provided
    if tags:
        instance_resource.tags = compute_v1.Tags(items=tags)

    # Add startup script if provided
    if startup_script_content:
        if instance_resource.metadata is None:
            instance_resource.metadata = compute_v1.Metadata()
        if instance_resource.metadata.items is None: # Initialize items list if it's None
            instance_resource.metadata.items = []
        instance_resource.metadata.items.append(
            compute_v1.Items(key="startup-script", value=startup_script_content)
        )

    try:
        print(f"ACTION: Creating instance '{instance_name}' in project '{project_id}', zone '{zone}'...")
        print(f"  Config: MachineType='{machine_type}', Image='{image_project}/{image_family}', Disk='{disk_size_gb}GB {disk_type}'")
        print(f"  Network: EphemeralIP='{assign_ephemeral_ip}', Tags='{tags if tags else 'None'}'")
        print(f"  Metadata: StartupScript='{'Provided' if startup_script_content else 'None'}'")

        operation = instance_client.insert(project=project_id, zone=zone, instance_resource=instance_resource)

        op_start_time = time.time()
        while operation.status != compute_v1.Operation.Status.DONE:
            time.sleep(5)
            # For zonal operations, use the InstancesClient's get method for the operation
            operation = instance_client.get(project=project_id, zone=zone, operation=operation.name)
            elapsed_time = time.time() - op_start_time
            print(f"INFO: Waiting for instance creation operation to complete... Status: {operation.status.name} (Elapsed: {elapsed_time:.0f}s)")
            if elapsed_time > 600: # 10 minutes timeout
                 print(f"ERROR: Timeout waiting for instance creation for '{instance_name}'.")
                 return False

        if operation.error:
            print(f"ERROR: Could not create instance '{instance_name}'. Error: {operation.error.errors}")
            return False

        print(f"SUCCESS: Instance '{instance_name}' created successfully.")
        return True
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while creating instance '{instance_name}': {e}")
        return False

def assign_static_ip_to_vm(project_id: str, zone: str, instance_name: str, ip_address: str, network_interface_name: str = "nic0") -> bool:
    """
    Assigns a static external IP address to a VM instance's network interface.

    Args:
        project_id: The ID of the Google Cloud project.
        zone: The zone where the instance exists.
        instance_name: The name of the VM instance.
        ip_address: The static IP address (string format) to assign.
        network_interface_name: The name of the network interface (default "nic0").

    Returns:
        True if IP assignment was successful, False otherwise.
    """
    instance_client = compute_v1.InstancesClient()

    try:
        print(f"ACTION: Assigning static IP {ip_address} to instance '{instance_name}' in zone '{zone}' (interface '{network_interface_name}')...")

        # Get the current instance details to find the fingerprint of the NIC
        current_instance = instance_client.get(project=project_id, zone=zone, instance=instance_name)
        if not current_instance.network_interfaces:
            print(f"ERROR: Instance '{instance_name}' has no network interfaces.")
            return False

        nic_to_update = None
        for nic in current_instance.network_interfaces:
            if nic.name == network_interface_name:
                nic_to_update = nic
                break

        if not nic_to_update:
            print(f"ERROR: Network interface '{network_interface_name}' not found on instance '{instance_name}'.")
            return False

        # Create a new AccessConfig with the static IP
        # Note: The name "External NAT" for the access config is a common convention.
        new_access_config = compute_v1.AccessConfig(
            name="External NAT",
            nat_i_p=ip_address,
            type_="ONE_TO_ONE_NAT", # Standard type for external IP
            network_tier="STANDARD" # Ensure this matches the reserved IP's tier
        )

        # Update the network interface. This replaces existing access_configs on the NIC.
        operation = instance_client.update_network_interface(
            project=project_id,
            zone=zone,
            instance=instance_name,
            network_interface=network_interface_name, # Name of the NIC (e.g., "nic0")
            network_interface_resource=compute_v1.NetworkInterface(
                name=nic_to_update.name,
                fingerprint=nic_to_update.fingerprint, # IMPORTANT: Fingerprint is required for updates
                access_configs=[new_access_config] # Set the new access config
            )
        )

        op_start_time = time.time()
        while operation.status != compute_v1.Operation.Status.DONE:
            time.sleep(5)
            operation = instance_client.get(project=project_id, zone=zone, operation=operation.name) # Poll zonal operation
            elapsed_time = time.time() - op_start_time
            print(f"INFO: Waiting for IP assignment operation to complete... Status: {operation.status.name} (Elapsed: {elapsed_time:.0f}s)")
            if elapsed_time > 300: # 5 minutes timeout
                 print(f"ERROR: Timeout waiting for IP assignment for '{instance_name}'.")
                 return False

        if operation.error:
            print(f"ERROR: Could not assign static IP to instance '{instance_name}'. Error: {operation.error.errors}")
            return False

        print(f"SUCCESS: Static IP {ip_address} assigned successfully to instance '{instance_name}'.")
        return True
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while assigning static IP to instance '{instance_name}': {e}")
        return False

# ##################################
# # Main Execution Block         #
# ##################################

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Deploy a ZNC VM on Google Cloud with static IP and firewall configuration.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Shows default values in help
    )

    # --- Project and Zone Configuration ---
    project_group = parser.add_argument_group("Project and Location")
    project_group.add_argument("--project-id", required=True, help="Google Cloud Project ID.")
    project_group.add_argument("--zone", default="us-west1-a", help="Compute zone for the VM instance (e.g., us-central1-a).")
    project_group.add_argument("--region", help="Region for static IP reservation (e.g., us-west1). If not provided, it's derived from the --zone.")

    # --- VM Instance Configuration ---
    vm_group = parser.add_argument_group("VM Instance Configuration")
    vm_group.add_argument("--instance-name", default="znc-bouncer-vm", help="Name for the VM instance.")
    vm_group.add_argument("--machine-type", default="e2-micro", help="Machine type for the VM (e.g., e2-medium, n1-standard-1).")
    vm_group.add_argument("--image-project", default="debian-cloud", help="Project for the boot image (e.g., debian-cloud, ubuntu-os-cloud).")
    vm_group.add_argument("--image-family", default="debian-11", help="Image family for the boot image (e.g., debian-11, ubuntu-2204-lts).")
    vm_group.add_argument("--disk-size-gb", type=int, default=10, help="Boot disk size in GB.")
    vm_group.add_argument("--disk-type", default="pd-balanced", help="Boot disk type (e.g., pd-standard, pd-balanced, pd-ssd).")
    vm_group.add_argument("--startup-script-path", default="startup-script.sh", help="Path to the local startup script file to be executed on VM boot.")

    # --- Networking Configuration ---
    network_group = parser.add_argument_group("Networking Configuration")
    network_group.add_argument("--static-ip-name", help="Name of the static IP address to reserve/use. If not provided, an ephemeral IP will be used for the VM.")
    network_group.add_argument("--network-tag", default="znc-bouncer-node", help="Network tag to apply to the VM instance. Used by the firewall rule.")

    # --- Firewall Configuration ---
    firewall_group = parser.add_argument_group("Firewall Configuration")
    firewall_group.add_argument("--firewall-rule-name", default="allow-znc-access", help="Name for the firewall rule to allow ZNC traffic.")
    firewall_group.add_argument("--znc-port", type=int, default=6697, help="Port number ZNC will listen on (this port will be opened in the firewall).")

    args = parser.parse_args()

    # Critical: Check for placeholder project ID
    if args.project_id == "your-gcp-project-id-here" or not args.project_id:
        print("CRITICAL ERROR: Please provide your Google Cloud Project ID using the --project-id argument.")
        sys.exit(1) # Use sys.exit for cleaner exit with error code

    # Determine region for static IP if not explicitly provided
    actual_region = args.region if args.region else args.zone.rsplit('-', 1)[0]

    # Read startup script content from the specified file path
    startup_script_content_main = None
    if args.startup_script_path:
        try:
            with open(args.startup_script_path, "r") as f:
                startup_script_content_main = f.read()
            print(f"INFO: Successfully read startup script from '{args.startup_script_path}'.")
        except FileNotFoundError:
            print(f"WARNING: Startup script file '{args.startup_script_path}' not found. Proceeding without a startup script.")
        except Exception as e:
            print(f"WARNING: Error reading startup script file '{args.startup_script_path}': {e}. Proceeding without a startup script.")

    # Initialize state variables
    vm_created_successfully = False
    static_ip_address_value = None # Store the actual IP address string if reserved/fetched
    reserved_ip_info = None # Store the Address object

    # --- Step 1: Reserve Static IP (if requested) ---
    if args.static_ip_name:
        print(f"\n--- Attempting to reserve/get static IP '{args.static_ip_name}' in region '{actual_region}' ---")
        reserved_ip_info = reserve_static_ip(args.project_id, actual_region, args.static_ip_name)
        if reserved_ip_info and reserved_ip_info.address:
            static_ip_address_value = reserved_ip_info.address
            print(f"INFO: Static IP '{reserved_ip_info.name}' is available at {static_ip_address_value}.")
        else:
            print(f"CRITICAL ERROR: Could not reserve or find static IP '{args.static_ip_name}'. Halting deployment.")
            sys.exit(1)
    else:
        print("\n--- Proceeding with an ephemeral IP address for the VM (no static IP name provided) ---")

    # --- Step 2: Create VM Instance ---
    print(f"\n--- Attempting to create VM instance '{args.instance_name}' ---")
    vm_tags = [args.network_tag] if args.network_tag else [] # Ensure tags is a list

    vm_created_successfully = create_vm_instance(
        project_id=args.project_id,
        zone=args.zone,
        instance_name=args.instance_name,
        machine_type=args.machine_type,
        image_project=args.image_project,
        image_family=args.image_family,
        disk_size_gb=args.disk_size_gb,
        disk_type=args.disk_type,
        assign_ephemeral_ip=(not args.static_ip_name), # Assign ephemeral only if not using static IP
        tags=vm_tags,
        startup_script_content=startup_script_content_main
    )

    if not vm_created_successfully:
        print(f"CRITICAL ERROR: VM instance '{args.instance_name}' creation failed. Halting deployment.")
        # Note: If static IP was reserved but VM creation failed, the IP remains reserved.
        # Consider adding logic to release the IP here if that's the desired behavior.
        sys.exit(1)

    # --- Step 3: Assign Static IP to VM (if static IP was used and VM created) ---
    # This step is only needed if we created the VM without an IP initially,
    # and now need to assign the reserved static IP.
    # The current create_vm_instance logic with assign_ephemeral_ip=False handles this by not adding any AccessConfig.
    # So, assign_static_ip_to_vm is crucial here.
    if args.static_ip_name and static_ip_address_value and vm_created_successfully:
        print(f"\n--- Attempting to assign static IP '{static_ip_address_value}' to VM '{args.instance_name}' ---")
        assign_success = assign_static_ip_to_vm(
            project_id=args.project_id,
            zone=args.zone,
            instance_name=args.instance_name,
            ip_address=static_ip_address_value
        )
        if not assign_success:
            print(f"ERROR: Failed to assign static IP to VM '{args.instance_name}'. The VM is created but may not have the desired external IP. Manual intervention might be needed.")
            # Don't halt here, firewall might still be useful, or user can fix IP manually.

    # --- Step 4: Create Firewall Rule (if VM created successfully) ---
    if vm_created_successfully:
        if args.network_tag and args.firewall_rule_name and args.znc_port:
            print(f"\n--- Attempting to create firewall rule '{args.firewall_rule_name}' ---")
            firewall_ports_to_allow = [f"tcp:{args.znc_port}"]
            network_uri = "global/networks/default" # Assuming default network

            firewall_success = create_firewall_rule(
                project_id=args.project_id,
                firewall_rule_name=args.firewall_rule_name,
                network_name=network_uri,
                target_tag=args.network_tag,
                allowed_ports=firewall_ports_to_allow
            )
            if firewall_success:
                print(f"INFO: Firewall rule '{args.firewall_rule_name}' is configured for tag '{args.network_tag}' on port {args.znc_port}.")
            else:
                print(f"ERROR: Firewall rule '{args.firewall_rule_name}' configuration failed. Please check logs and configure manually if needed.")
        elif args.network_tag or args.firewall_rule_name or args.znc_port: # If some firewall args are present but not all
             print("\nWARNING: Firewall rule creation was skipped because one or more of --network-tag, --firewall-rule-name, or --znc-port were not specified. All are required for firewall setup.")


    # --- Final Summary ---
    print(f"\n--- ZNC VM Deployment Summary for Instance '{args.instance_name}' ---")
    if vm_created_successfully:
        print(f"  VM Status: Successfully deployed.")
        if args.static_ip_name:
            if static_ip_address_value and assign_success: # Check if assignment was attempted and successful
                 print(f"  IP Address: Configured with Static IP '{static_ip_address_value}' (Name: {args.static_ip_name}).")
            elif static_ip_address_value: # IP reserved but assignment failed
                 print(f"  IP Address: Attempted Static IP '{static_ip_address_value}' (Name: {args.static_ip_name}) - ASSIGNMENT FAILED. Check logs.")
            else: # Should not happen if static_ip_name is set and reservation succeeded.
                 print(f"  IP Address: Static IP '{args.static_ip_name}' was intended but value is missing.")
        else:
            print(f"  IP Address: Configured with an Ephemeral IP. Check Google Cloud Console for the address.")

        if args.firewall_rule_name and firewall_success:
            print(f"  Firewall: Rule '{args.firewall_rule_name}' active for port TCP:{args.znc_port} on tag '{args.network_tag}'.")
        elif args.firewall_rule_name:
             print(f"  Firewall: Rule '{args.firewall_rule_name}' configuration ATTEMPTED BUT FAILED or was skipped. Check logs.")
        else:
            print(f"  Firewall: No specific firewall rule was configured by this script for ZNC port (or arguments missing).")

        if startup_script_content_main:
            print(f"  Startup Script: Was provided from '{args.startup_script_path}'. Check VM logs for execution details (/var/log/startup-script.log).")
        else:
            print(f"  Startup Script: Not provided or file not found at '{args.startup_script_path}'.")

        print("\nNEXT STEPS:")
        print(f"1. Connect to the VM (e.g., via SSH using gcloud or the console).")
        print(f"2. Check ZNC status: `sudo systemctl status znc.service`")
        print(f"3. Check startup script logs: `sudo cat /var/log/startup-script.log`")
        print(f"4. Configure ZNC: `sudo -u zncuser znc --makeconf` (if not handled by startup script or if customization is needed).")

    else:
        print(f"  VM Status: Deployment FAILED. See error messages above.")

    print("--- End of Deployment ---")
