import argparse
import sys
import time # Will be needed for waiting on operations
from google.cloud import compute_v1
from google.api_core.exceptions import NotFound # For checking if a resource exists before deletion

# Placeholder/Stub functions for deletion operations
def delete_vm_instance(project_id: str, zone: str, instance_name: str) -> bool:
    """
    Deletes a VM instance from the specified project and zone.

    Args:
        project_id: The ID of the Google Cloud project.
        zone: The zone where the instance exists.
        instance_name: The name of the VM instance to delete.

    Returns:
        True if deletion was successful or instance was not found, False otherwise.
    """
    instance_client = compute_v1.InstancesClient()
    zone_operation_client = compute_v1.ZoneOperationsClient()

    try:
        print(f"ACTION: Deleting instance '{instance_name}' in project '{project_id}', zone '{zone}'...")
        operation = instance_client.delete(
            project=project_id,
            zone=zone,
            instance=instance_name
        )

        # Wait for the operation to complete
        op_start_time = time.time()
        while operation.status != compute_v1.Operation.Status.DONE:
            time.sleep(5) # Poll every 5 seconds
            operation = zone_operation_client.get(project=project_id, zone=zone, operation=operation.name)
            elapsed_time = time.time() - op_start_time
            print(f"INFO: Waiting for instance deletion operation for '{instance_name}' to complete... Status: {operation.status.name} (Elapsed: {elapsed_time:.0f}s)")

            if elapsed_time > 600: # 10 minutes timeout
                print(f"ERROR: Timeout waiting for instance '{instance_name}' deletion after {elapsed_time:.0f} seconds.")
                # Check operation status one last time or handle as per policy
                if operation.error:
                     print(f"ERROR details (timeout): {operation.error.errors}")
                return False

        if operation.error:
            print(f"ERROR: Could not delete instance '{instance_name}'. Error details: {operation.error.errors}")
            # Check for specific errors, e.g. if it's due to resource being in use by another operation
            for error_detail in operation.error.errors:
                if error_detail.code == 'RESOURCE_IN_USE_BY_ANOTHER_RESOURCE':
                    print("INFO: Instance might be in use or has dependent resources (like attached disks set to not auto-delete).")
            return False

        print(f"SUCCESS: Instance '{instance_name}' deleted successfully from zone '{zone}'.")
        return True

    except NotFound:
        print(f"INFO: Instance '{instance_name}' not found in project '{project_id}', zone '{zone}'. Considered deleted.")
        return True
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while deleting instance '{instance_name}': {e}")
        return False

def delete_static_ip(project_id: str, region: str, static_ip_name: str) -> bool:
    """
    Deletes a static external IP address from the specified project and region.

    Args:
        project_id: The ID of the Google Cloud project.
        region: The region where the static IP address exists.
        static_ip_name: The name of the static IP address to delete.

    Returns:
        True if deletion was successful or the address was not found, False otherwise.
    """
    address_client = compute_v1.AddressesClient()
    region_operation_client = compute_v1.RegionOperationsClient()

    try:
        print(f"ACTION: Deleting static IP address '{static_ip_name}' in project '{project_id}', region '{region}'...")
        operation = address_client.delete(
            project=project_id,
            region=region,
            address=static_ip_name
        )

        # Wait for the regional operation to complete
        op_start_time = time.time()
        while operation.status != compute_v1.Operation.Status.DONE:
            time.sleep(5) # Poll every 5 seconds
            operation = region_operation_client.get(project=project_id, region=region, operation=operation.name)
            elapsed_time = time.time() - op_start_time
            print(f"INFO: Waiting for static IP deletion operation for '{static_ip_name}' to complete... Status: {operation.status.name} (Elapsed: {elapsed_time:.0f}s)")

            if elapsed_time > 300: # 5 minutes timeout
                print(f"ERROR: Timeout waiting for static IP '{static_ip_name}' deletion after {elapsed_time:.0f} seconds.")
                if operation.error: # Log error details if available on timeout
                     print(f"ERROR details (timeout): {operation.error.errors}")
                return False

        if operation.error:
            print(f"ERROR: Could not delete static IP '{static_ip_name}'. Error details: {operation.error.errors}")
            return False

        print(f"SUCCESS: Static IP address '{static_ip_name}' deleted successfully from region '{region}'.")
        return True

    except NotFound:
        print(f"INFO: Static IP address '{static_ip_name}' not found in project '{project_id}', region '{region}'. Considered deleted.")
        return True
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while deleting static IP '{static_ip_name}': {e}")
        return False

def delete_firewall_rule(project_id: str, firewall_rule_name: str) -> bool:
    """
    Deletes a firewall rule from the specified project.

    Args:
        project_id: The ID of the Google Cloud project.
        firewall_rule_name: The name of the firewall rule to delete.

    Returns:
        True if deletion was successful or the rule was not found, False otherwise.
    """
    firewall_client = compute_v1.FirewallsClient()
    global_operation_client = compute_v1.GlobalOperationsClient()

    try:
        print(f"ACTION: Deleting firewall rule '{firewall_rule_name}' in project '{project_id}'...")
        operation = firewall_client.delete(
            project=project_id,
            firewall=firewall_rule_name
        )

        # Wait for the global operation to complete
        op_start_time = time.time()
        while operation.status != compute_v1.Operation.Status.DONE:
            time.sleep(5) # Poll every 5 seconds
            operation = global_operation_client.get(project=project_id, operation=operation.name)
            elapsed_time = time.time() - op_start_time
            print(f"INFO: Waiting for firewall rule deletion operation for '{firewall_rule_name}' to complete... Status: {operation.status.name} (Elapsed: {elapsed_time:.0f}s)")

            if elapsed_time > 300: # 5 minutes timeout
                print(f"ERROR: Timeout waiting for firewall rule '{firewall_rule_name}' deletion after {elapsed_time:.0f} seconds.")
                if operation.error: # Log error details if available on timeout
                     print(f"ERROR details (timeout): {operation.error.errors}")
                return False

        if operation.error:
            print(f"ERROR: Could not delete firewall rule '{firewall_rule_name}'. Error details: {operation.error.errors}")
            return False

        print(f"SUCCESS: Firewall rule '{firewall_rule_name}' deleted successfully from project '{project_id}'.")
        return True

    except NotFound:
        print(f"INFO: Firewall rule '{firewall_rule_name}' not found in project '{project_id}'. Considered deleted.")
        return True
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while deleting firewall rule '{firewall_rule_name}': {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Undeploy ZNC VM and associated resources from Google Cloud.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # --- Required Arguments ---
    req_group = parser.add_argument_group("Required Arguments")
    req_group.add_argument("--project-id", required=True, help="Google Cloud Project ID.")
    req_group.add_argument("--zone", required=True, help="Compute zone of the VM instance (e.g., us-central1-c).")

    # --- VM Deletion Arguments ---
    vm_group = parser.add_argument_group("VM Deletion")
    vm_group.add_argument("--instance-name", default="znc-bouncer-vm", help="Name of the VM instance to delete.")

    # --- Static IP Deletion Arguments ---
    ip_group = parser.add_argument_group("Static IP Deletion")
    ip_group.add_argument("--static-ip-name", help="Name of the static IP address to delete. If not provided, static IP deletion will be skipped.")
    ip_group.add_argument("--region", help="Region of the static IP address. Required if --static-ip-name is provided; can be derived from --zone if not set.")

    # --- Firewall Deletion Arguments ---
    fw_group = parser.add_argument_group("Firewall Deletion")
    fw_group.add_argument("--firewall-rule-name", default="allow-znc-access", help="Name of the firewall rule to delete.")

    # --- Control Arguments ---
    control_group = parser.add_argument_group("Control Arguments")
    control_group.add_argument("--yes", action='store_true', default=False, help="Bypass interactive confirmation for deletions.")

    args = parser.parse_args()

    # --- Initial Checks and Setup ---
    if not args.project_id: # Redundant due to required=True, but good practice
        print("ERROR: --project-id is required.")
        sys.exit(1)

    print(f"--- ZNC Undeployment Script ---")
    print(f"Project ID: {args.project_id}")
    print(f"Zone: {args.zone}")

    # Derive region from zone if static IP name is provided and region is not
    if args.static_ip_name and not args.region:
        if args.zone:
            args.region = args.zone.rsplit('-', 1)[0]
            print(f"INFO: Derived region '{args.region}' from zone '{args.zone}' for static IP deletion.")
        else:
            # This case should ideally be caught by argparse if zone is always required with static-ip-name logic,
            # but an explicit check is safer. Zone is already required=True, so this path might be hard to reach.
            print("ERROR: --zone is required to derive the region for static IP deletion if --region is not explicitly provided.")
            sys.exit(1)
    elif args.static_ip_name and args.region:
        print(f"Region for Static IP: {args.region}")


    # --- Summary of Actions ---
    print("\n--- Planned Actions ---")
    print(f"1. Delete VM Instance: '{args.instance_name}' in zone '{args.zone}'.")
    if args.static_ip_name:
        if args.region:
            print(f"2. Delete Static IP: '{args.static_ip_name}' in region '{args.region}'.")
        else: # Should not happen due to derivation logic or if region becomes required with static_ip_name
            print(f"WARNING: Static IP '{args.static_ip_name}' specified, but region is missing. Skipping its deletion.")
    else:
        print("2. Delete Static IP: Skipped (no --static-ip-name provided).")

    if args.firewall_rule_name:
        print(f"3. Delete Firewall Rule: '{args.firewall_rule_name}'.")
    else:
        print("3. Delete Firewall Rule: Skipped (no --firewall-rule-name provided).")


    # --- Confirmation (Placeholder for now) ---
    if not args.yes:
        print("\nIMPORTANT: This script will attempt to delete the resources listed above.")
        confirmation = input("Are you sure you want to proceed? (yes/no): ")
        if confirmation.lower() != 'yes':
            print("Undeployment aborted by user.")
            sys.exit(0)
        print("Proceeding with undeployment...")
    else:
        print("\nINFO: --yes flag detected, bypassing confirmation.")

    # --- Execute Deletion Operations ---
    print("\n--- Starting Deprovisioning Process ---")
    results = {
        "vm": "NOT_ATTEMPTED",
        "static_ip": "NOT_ATTEMPTED",
        "firewall": "NOT_ATTEMPTED"
    }

    # 1. Delete VM Instance
    print("\n--- Deleting VM Instance ---")
    if delete_vm_instance(args.project_id, args.zone, args.instance_name):
        results["vm"] = "DELETED"
        print(f"INFO: VM Instance '{args.instance_name}' deletion successful or already deleted.")
    else:
        results["vm"] = "FAILED"
        print(f"ERROR: VM Instance '{args.instance_name}' deletion failed. Check logs above.")

    # 2. Delete Static IP Address (if specified)
    if args.static_ip_name:
        print("\n--- Deleting Static IP Address ---")
        actual_region_for_ip = args.region # Region might have been derived earlier or provided
        if not actual_region_for_ip: # Should have been caught by initial derivation, but double check
            print(f"ERROR: Region for static IP '{args.static_ip_name}' could not be determined (was --zone provided?). Skipping IP deletion.")
            results["static_ip"] = "FAILED (Missing Region)"
        else:
            if delete_static_ip(args.project_id, actual_region_for_ip, args.static_ip_name):
                results["static_ip"] = "DELETED"
                print(f"INFO: Static IP '{args.static_ip_name}' deletion successful or already deleted from region '{actual_region_for_ip}'.")
            else:
                results["static_ip"] = "FAILED"
                print(f"ERROR: Static IP '{args.static_ip_name}' deletion failed in region '{actual_region_for_ip}'. Check logs above.")
    else:
        results["static_ip"] = "SKIPPED (Not Provided)"
        print("\n--- Deleting Static IP Address: SKIPPED (No --static-ip-name provided) ---")


    # 3. Delete Firewall Rule
    # firewall_rule_name has a default, so it will usually be attempted unless user explicitly provides an empty string.
    if args.firewall_rule_name:
        print("\n--- Deleting Firewall Rule ---")
        if delete_firewall_rule(args.project_id, args.firewall_rule_name):
            results["firewall"] = "DELETED"
            print(f"INFO: Firewall Rule '{args.firewall_rule_name}' deletion successful or already deleted.")
        else:
            results["firewall"] = "FAILED"
            print(f"ERROR: Firewall Rule '{args.firewall_rule_name}' deletion failed. Check logs above.")
    else:
        # This case is unlikely given the default value for firewall_rule_name.
        results["firewall"] = "SKIPPED (No Name Provided)"
        print("\n--- Deleting Firewall Rule: SKIPPED (No --firewall-rule-name provided) ---")

    # --- Final Summary ---
    print("\n\n--- Deprovisioning Summary ---")
    print(f"  VM Instance ('{args.instance_name}'): {results['vm']}")

    if args.static_ip_name: # Only show static IP details if it was part of the command
        print(f"  Static IP ('{args.static_ip_name}', Region: '{args.region if args.region else 'Derived from zone'}'): {results['static_ip']}")
    else:
        print(f"  Static IP: {results['static_ip']}") # Will show SKIPPED

    if args.firewall_rule_name: # Only show firewall details if it was part of the command (it has a default)
        print(f"  Firewall Rule ('{args.firewall_rule_name}'): {results['firewall']}")
    else:
        print(f"  Firewall Rule: {results['firewall']}") # Will show SKIPPED

    print("\nDeprovisioning process complete. Please review the logs above for details and verify resource deletion in the Google Cloud Console.")
