import os
import random
import string
import subprocess
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerinstance.models import (
    ContainerGroup,
    Container,
    ContainerPort,
    EnvironmentVariable,
    ImageRegistryCredential,
    IpAddress,
    OperatingSystemTypes,
    Port,
    ResourceRequests,
    ResourceRequirements,
)
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError

# --- Configuration ---
# Replace with your actual values or fetch dynamically
# If AZURE_SUBSCRIPTION_ID is not set, it will try to fetch from 'az account show'
AZURE_SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP_NAME = "hello-rg-04042025" # Replace if different
ACR_LOGIN_SERVER = "helloacr04042025.azurecr.io" # Replace if different
IMAGE_NAME = "azure-hello" # Image name in ACR
IMAGE_TAG = "latest" # Image tag
CONTAINER_INSTANCE_NAME = "azure-hello-py-sdk" # Name for the ACI
DNS_NAME_LABEL_BASE = "azure-hello-app-py" # Base for the public DNS name
CONTAINER_PORT = 8501 # Port exposed by the container (from Dockerfile)
CPU_CORES = 1.0
MEMORY_IN_GB = 1.5

# --- Helper Functions ---

def get_subscription_id(credential):
    """Gets the subscription ID from env or Azure CLI."""
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    if subscription_id:
        print(f"Using Subscription ID from environment: {subscription_id}")
        return subscription_id

    print("Warning: AZURE_SUBSCRIPTION_ID environment variable not set.")
    print("Attempting to fetch default subscription ID from Azure CLI...")
    try:
        result = subprocess.run(
            ["az", "account", "show", "--query", "id", "-o", "tsv"],
            capture_output=True, text=True, check=True, shell=False
        )
        subscription_id = result.stdout.strip()
        if not subscription_id:
            print("Error: Azure CLI did not return a subscription ID.")
            return None
        print(f"Successfully fetched subscription ID from Azure CLI: {subscription_id}")
        return subscription_id
    except FileNotFoundError:
        print("Error: Azure CLI ('az') command not found.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error: Azure CLI command failed: {e}")
        print(f"Stderr: {e.stderr.strip()}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while running Azure CLI: {e}")
        return None

def get_resource_group_location(credential, subscription_id, rg_name):
    """Gets the location of the specified resource group."""
    try:
        resource_client = ResourceManagementClient(credential, subscription_id)
        rg = resource_client.resource_groups.get(rg_name)
        return rg.location
    except HttpResponseError as e:
        print(f"Error fetching resource group '{rg_name}': {e}")
        if e.status_code == 404:
            print(f"Resource group '{rg_name}' not found.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred fetching resource group: {e}")
        return None

def generate_unique_dns_label(base_label):
    """Generates a unique DNS label."""
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{base_label}-{random_suffix}"

# --- Main Deployment Logic ---

def deploy_container_instance():
    """Deploys the container instance to Azure."""
    try:
        # --- Authentication ---
        print("Authenticating...")
        credential = DefaultAzureCredential()

        # --- Get Subscription ID ---
        subscription_id = get_subscription_id(credential)
        if not subscription_id:
            print("Deployment aborted: Could not determine Subscription ID.")
            return

        # --- Get Resource Group Location ---
        print(f"Fetching location for resource group '{RESOURCE_GROUP_NAME}'...")
        location = get_resource_group_location(credential, subscription_id, RESOURCE_GROUP_NAME)
        if not location:
            print("Deployment aborted: Could not determine resource group location.")
            return
        print(f"Resource group location: {location}")

        # --- Initialize Container Instance Client ---
        print("Initializing Container Instance client...")
        aci_client = ContainerInstanceManagementClient(credential, subscription_id)

        # --- Configure Container ---
        print("Configuring container details...")
        full_image_name = f"{ACR_LOGIN_SERVER}/{IMAGE_NAME}:{IMAGE_TAG}"
        dns_name_label = generate_unique_dns_label(DNS_NAME_LABEL_BASE)

        # Important: Enable admin user on ACR to allow ACI to pull image
        # You might need to run: `az acr update -n <your_acr_name> --admin-enabled true`
        # For production, consider service principals or managed identities instead of admin user.
        # Fetch ACR credentials if admin user is enabled (requires 'az cli')
        print("Fetching ACR credentials (requires admin user enabled on ACR)...")
        try:
            # Ensure you are logged into Azure CLI
            # This assumes the user running the script has permission to get ACR credentials
            cred_result = subprocess.run(
                ["az", "acr", "credential", "show", "--name", ACR_LOGIN_SERVER.split('.')[0], "--query", "[username, passwords[0].value]", "-o", "tsv"],
                capture_output=True, text=True, check=True, shell=False
            )
            # Use newline as delimiter based on observed 'az cli' output format
            acr_username, acr_password = cred_result.stdout.strip().split('\n')
            if not acr_username or not acr_password:
                 raise ValueError("Could not retrieve ACR credentials.")
            print("Successfully fetched ACR credentials.")
            image_registry_creds = [
                ImageRegistryCredential(
                    server=ACR_LOGIN_SERVER,
                    username=acr_username,
                    password=acr_password
                )
            ]
        except FileNotFoundError:
            print("Error: Azure CLI ('az') command not found. Needed to fetch ACR credentials.")
            print("Hint: You might need to manually enable the admin user on the ACR and provide credentials.")
            image_registry_creds = None # Continue without creds, might fail if image is private
        except subprocess.CalledProcessError as e:
            print(f"Error fetching ACR credentials: {e}")
            print(f"Stderr: {e.stderr.strip()}")
            print("Hint: Ensure the ACR admin user is enabled ('az acr update -n <acr_name> --admin-enabled true') and you have permissions.")
            image_registry_creds = None # Continue without creds, might fail if image is private
        except Exception as e:
             print(f"An unexpected error occurred fetching ACR credentials: {e}")
             image_registry_creds = None


        container_resource_requests = ResourceRequests(memory_in_gb=MEMORY_IN_GB, cpu=CPU_CORES)
        container_resource_requirements = ResourceRequirements(requests=container_resource_requests)

        container = Container(
            name=CONTAINER_INSTANCE_NAME,
            image=full_image_name,
            resources=container_resource_requirements,
            ports=[ContainerPort(port=CONTAINER_PORT)]
        )

        # --- Configure Container Group ---
        group = ContainerGroup(
            location=location,
            containers=[container],
            os_type=OperatingSystemTypes.LINUX,
            restart_policy="Always", # Or "OnFailure", "Never"
            ip_address=IpAddress(
                ports=[Port(protocol="TCP", port=CONTAINER_PORT)],
                type="Public", # Public IP address
                dns_name_label=dns_name_label
            ),
            image_registry_credentials=image_registry_creds # Add credentials if fetched
        )

        # --- Create Container Group ---
        print(f"Creating container group '{CONTAINER_INSTANCE_NAME}' in resource group '{RESOURCE_GROUP_NAME}'...")
        poller = aci_client.container_groups.begin_create_or_update(RESOURCE_GROUP_NAME, CONTAINER_INSTANCE_NAME, group)
        created_group = poller.result() # Wait for deployment to complete

        print("Deployment successful!")
        print(f"Container Instance Name: {created_group.name}")
        if created_group.ip_address and created_group.ip_address.fqdn:
            print(f"FQDN: http://{created_group.ip_address.fqdn}:{CONTAINER_PORT}")
        else:
            print("FQDN not available immediately. Check Azure portal.")

    except ClientAuthenticationError:
        print("Error: Authentication failed.")
        print("Please ensure you are logged in via 'az login' or have configured credentials correctly (e.g., environment variables).")
    except HttpResponseError as e:
        print(f"Error: An Azure API error occurred: {e}")
        if "SubscriptionNotFound" in str(e):
             print("Hint: Double-check if the AZURE_SUBSCRIPTION_ID is correct and accessible by the credential.")
        if "ResourceGroupNotFound" in str(e):
            print(f"Hint: Ensure the resource group '{RESOURCE_GROUP_NAME}' exists.")
        if "InvalidImage" in str(e) or "ImagePullBackOff" in str(e) or "AcrUnauthorized" in str(e):
             print(f"Hint: Check if the image '{full_image_name}' exists and the ACR credentials/permissions are correct.")
             print(f"Hint: Make sure the ACR admin user is enabled: 'az acr update -n {ACR_LOGIN_SERVER.split('.')[0]} --admin-enabled true'")
        # Add more specific error handling as needed
    except Exception as e:
        print(f"An unexpected error occurred during deployment: {e}")

if __name__ == "__main__":
    deploy_container_instance() 