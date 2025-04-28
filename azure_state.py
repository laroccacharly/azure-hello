import os
import subprocess
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.containerregistry import ContainerRegistryManagementClient
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError

# Prerequisites:
# 1. Install required packages:
#    pip install azure-identity azure-mgmt-resource azure-mgmt-containerregistry
# 2. Authenticate with Azure:
#    - Run 'az login' in your terminal OR
#    - Set environment variables: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET, AZURE_SUBSCRIPTION_ID

def get_azure_state():
    """
    Connects to Azure and lists resource groups and container registries.
    """
    try:
        # --- Authentication ---
        # Use DefaultAzureCredential which checks common credential sources
        # (environment variables, managed identity, Azure CLI, etc.)
        credential = DefaultAzureCredential()

        # --- Get Subscription ID ---
        # Try getting subscription ID from environment variable first
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        if not subscription_id:
            print("Warning: AZURE_SUBSCRIPTION_ID environment variable not set.")
            print("Attempting to fetch default subscription ID from Azure CLI...")
            try:
                # Run 'az account show' command
                result = subprocess.run(
                    ["az", "account", "show", "--query", "id", "-o", "tsv"],
                    capture_output=True, text=True, check=True, shell=False # Use shell=False for security
                )
                subscription_id = result.stdout.strip() # Get the output and remove leading/trailing whitespace
                if not subscription_id:
                    print("Error: Azure CLI did not return a subscription ID. Is it configured with a default subscription?")
                    return
                print(f"Successfully fetched subscription ID from Azure CLI: {subscription_id}")
            except FileNotFoundError:
                print("Error: Azure CLI ('az') command not found. Please install it or set the AZURE_SUBSCRIPTION_ID environment variable.")
                return
            except subprocess.CalledProcessError as e:
                print(f"Error: Azure CLI command failed: {e}")
                print("Hint: Are you logged in to Azure CLI ('az login')?")
                print(f"Stderr: {e.stderr.strip()}")
                return
            except Exception as e:
                print(f"An unexpected error occurred while running Azure CLI: {e}")
                return

        # Ensure subscription_id is not None before proceeding
        if not subscription_id:
             print("Error: Could not determine Azure Subscription ID.")
             return

        print(f"\nUsing Subscription ID: {subscription_id}")

        # --- List Resource Groups ---
        print("\n--- Resource Groups ---")
        resource_client = ResourceManagementClient(credential, subscription_id)
        resource_groups = resource_client.resource_groups.list()

        rg_count = 0
        for rg in resource_groups:
            print(f"- Name: {rg.name}, Location: {rg.location}")
            rg_count += 1
        if rg_count == 0:
            print("No resource groups found in this subscription.")

        # --- List Container Registries ---
        print("\n--- Container Registries (ACR) ---")
        acr_client = ContainerRegistryManagementClient(credential, subscription_id)
        registries = acr_client.registries.list()

        acr_count = 0
        for reg in registries:
            # Get the resource group name from the registry ID
            # ID format: /subscriptions/.../resourceGroups/RG_NAME/providers/...
            
            try:
                rg_name = reg.id.split('/')[4]
            except IndexError:
                rg_name = "Unknown" # Should not happen with valid IDs

            print(f"- Name: {reg.name}, Resource Group: {rg_name}, Location: {reg.location}, SKU: {reg.sku.name}, Login Server: {reg.login_server}")
            acr_count += 1

            # List repositories in the registry
            print("\n--- Repositories in the registry ---")
            # az acr repository list --name helloacr04042025 --output table
            output = subprocess.run(["az", "acr", "repository", "list", "--name", reg.name, "--output", "table"], check=True, text=True, capture_output=True, shell=False)
            print(output.stdout)

            
        if acr_count == 0:
            print("No container registries found in this subscription.")

    except ClientAuthenticationError:
        print("\nError: Authentication failed.")
        print("Please ensure you are logged in via 'az login' or have configured credentials correctly (e.g., environment variables).")
    except HttpResponseError as e:
        print(f"\nError: An Azure API error occurred: {e}")
        if "SubscriptionNotFound" in str(e):
             print("Hint: Double-check if the AZURE_SUBSCRIPTION_ID is correct and accessible by the credential.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    get_azure_state() 