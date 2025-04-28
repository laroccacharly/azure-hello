import os
import time
import random
import docker

from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.containerregistry import ContainerRegistryManagementClient
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.authorization import AuthorizationManagementClient
from azure.mgmt.containerinstance.models import (
    ContainerGroup,
    Container,
    ImageRegistryCredential,
    ContainerGroupIdentity,
    ResourceRequests,
    ResourceRequirements,
    ContainerPort,
    IpAddress,
    Port
)

# --- Configuration ---
SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID") # Or replace with your subscription ID
RESOURCE_GROUP_NAME = "hello-rg-04042025"
ACR_NAME = "helloacr04042025" # Must be globally unique
ACI_NAME = "streamlit-hello-app-sdk" # Name for the ACI instance
LOCATION = "eastus"
DOCKER_IMAGE_NAME_BASE = "streamlit-hello"
DOCKER_IMAGE_TAG = "v1"
ACI_DNS_LABEL = f"streamlit-sdk-final-{random.randint(1000,9999)}"
ACR_PULL_ROLE_ID = "/providers/Microsoft.Authorization/roleDefinitions/7f951dda-4ed3-4680-a7ca-43fe172d538d" # AcrPull Role Definition ID


def main():
    if not SUBSCRIPTION_ID:
        print("Error: AZURE_SUBSCRIPTION_ID environment variable not set.")
        print("Please set it or replace os.environ.get(...) with your actual Subscription ID.")
        return

    # --- Authenticate ---
    print("Authenticating...")
    credential = DefaultAzureCredential()

    # --- Initialize Clients ---
    print("Initializing Azure clients...")
    resource_client = ResourceManagementClient(credential, SUBSCRIPTION_ID)
    acr_client = ContainerRegistryManagementClient(credential, SUBSCRIPTION_ID)
    aci_client = ContainerInstanceManagementClient(credential, SUBSCRIPTION_ID)
    auth_client = AuthorizationManagementClient(credential, SUBSCRIPTION_ID)
    docker_client = docker.from_env()

    # --- Create Resource Group ---
    print(f"Creating/Updating Resource Group: {RESOURCE_GROUP_NAME}...")
    rg_result = resource_client.resource_groups.create_or_update(
        RESOURCE_GROUP_NAME, {"location": LOCATION}
    )
    print(f"Resource Group '{rg_result.name}' created/updated in {rg_result.location}.")

    # --- Create ACR ---
    print(f"Creating/Updating ACR: {ACR_NAME}...")
    acr_poller = acr_client.registries.begin_create(
        RESOURCE_GROUP_NAME,
        ACR_NAME,
        {
            "location": LOCATION,
            "sku": {"name": "Basic"},
            "admin_user_enabled": True, # Needed to get credentials for docker push/initial ACI pull
        },
    )
    acr_result = acr_poller.result()
    acr_login_server = acr_result.login_server
    print(f"ACR '{acr_result.name}' created/updated. Login server: {acr_login_server}")

    # --- Get ACR Credentials ---
    print("Fetching ACR credentials...")
    acr_credentials = acr_client.registries.list_credentials(
        RESOURCE_GROUP_NAME, ACR_NAME
    )
    acr_username = acr_credentials.username
    acr_password = acr_credentials.passwords[0].value # Use first password
    print("ACR credentials obtained.")

    # --- Build Docker Image (Platform Specific) ---
    local_image_tag = f"{DOCKER_IMAGE_NAME_BASE}:latest"
    print(f"Building Docker image {local_image_tag} for linux/amd64...")
    try:
        image, build_log = docker_client.images.build(
            path=".",
            tag=local_image_tag,
            rm=True,
            forcerm=True,
            platform="linux/amd64" # Explicitly set platform
        )
        print(f"Image built: {image.id}")
        # for line in build_log:
        #     if 'stream' in line:
        #         print(line['stream'].strip())
    except docker.errors.BuildError as e:
        print(f"Docker build failed: {e}")
        for line in e.build_log:
             if 'stream' in line:
                 print(line['stream'].strip())
        return
    except Exception as e:
        print(f"An error occurred during docker build: {e}")
        return


    # --- Tag Docker Image for ACR ---
    acr_image_tag = f"{acr_login_server}/{DOCKER_IMAGE_NAME_BASE}:{DOCKER_IMAGE_TAG}"
    print(f"Tagging image for ACR: {acr_image_tag}...")
    if image.tag(acr_image_tag):
        print("Image tagged successfully.")
    else:
        print("Failed to tag image.")
        return

    # --- Push Docker Image to ACR ---
    print(f"Pushing image {acr_image_tag} to ACR...")
    try:
        push_log = docker_client.images.push(
            repository=acr_image_tag,
            auth_config={"username": acr_username, "password": acr_password},
            stream=True,
            decode=True
        )
        for line in push_log:
            # print(line) # Uncomment for detailed push progress
            if 'error' in line:
                print(f"Error pushing image: {line['error']}")
                return
        print("Image pushed successfully.")
    except Exception as e:
        print(f"An error occurred during docker push: {e}")
        return

    # --- Create ACI ---
    print(f"Creating ACI: {ACI_NAME}...")
    aci_poller = aci_client.container_groups.begin_create_or_update(
        RESOURCE_GROUP_NAME,
        ACI_NAME,
        ContainerGroup(
            location=LOCATION,
            os_type="Linux", # Specify OS Type
            identity=ContainerGroupIdentity(type="SystemAssigned"), # Assign System Identity
            containers=[
                Container(
                    name=ACI_NAME, # Container name often matches ACI name
                    image=acr_image_tag,
                    resources=ResourceRequirements(
                        requests=ResourceRequests(memory_in_gb=1.0, cpu=1.0) # Specify resources
                    ),
                    ports=[ContainerPort(port=8501)] # Expose Streamlit port
                )
            ],
            image_registry_credentials=[ # Provide credentials for initial pull
                ImageRegistryCredential(
                    server=acr_login_server,
                    username=acr_username,
                    password=acr_password,
                )
            ],
            ip_address=IpAddress(
                type="Public",
                ports=[Port(protocol="TCP", port=8501)],
                dns_name_label=ACI_DNS_LABEL # Unique DNS label
            ),
        ),
    )
    aci_result = aci_poller.result()
    aci_principal_id = aci_result.identity.principal_id
    aci_id = aci_result.id
    print(f"ACI '{aci_result.name}' created successfully.")
    print(f"  FQDN: {aci_result.ip_address.fqdn}")
    print(f"  IP: {aci_result.ip_address.ip}")
    print(f"  Managed Identity Principal ID: {aci_principal_id}")

    # --- Assign AcrPull Role to ACI Managed Identity ---
    print("Assigning AcrPull role to ACI Managed Identity...")
    # Construct the scope for the ACR
    acr_scope = f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP_NAME}/providers/Microsoft.ContainerRegistry/registries/{ACR_NAME}"
    # Generate a unique name for the role assignment
    role_assignment_name = f"acrpull-role-{random.randint(10000, 99999)}"

    role_assignment_result = auth_client.role_assignments.create(
        scope=acr_scope,
        role_assignment_name=role_assignment_name,
        parameters={
            "role_definition_id": f"/subscriptions/{SUBSCRIPTION_ID}{ACR_PULL_ROLE_ID}",
            "principal_id": aci_principal_id,
        },
    )
    print(f"Role assignment '{role_assignment_result.name}' created.")

    # Wait briefly for role assignment propagation
    print("Waiting 30 seconds for role assignment to propagate...")
    time.sleep(30)

    print("\nDeployment complete!")
    print(f"Access your Streamlit app at: http://{aci_result.ip_address.fqdn}:8501")
    print(f"Or using the IP: http://{aci_result.ip_address.ip}:8501")

    # --- Stop ACI (Optional - uncomment to stop after deployment) ---
    # print(f"\nStopping ACI instance: {ACI_NAME}...")
    # aci_client.container_groups.stop(RESOURCE_GROUP_NAME, ACI_NAME)
    # print("ACI instance stopped.")

if __name__ == "__main__":
    main()