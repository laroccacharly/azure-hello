Local Setup: Created app.py (Streamlit app), requirements.txt, and Dockerfile.
Docker Build (Platform Specific): Built the Docker image locally, initially encountering an OS mismatch error when deploying to ACI. Rebuilt the image specifying the --platform linux/amd64 to ensure compatibility with ACI's infrastructure.
Azure Login: Logged into Azure using az login.
Resource Group Creation: Created an Azure Resource Group (hello-rg-04042025) using az group create.
ACR Creation: Created an Azure Container Registry (helloacr04042025) with the admin user enabled using az acr create.
ACR Login & Image Push: Logged into the ACR (az acr login) and pushed the locally built (and correctly platform-tagged) Docker image (streamlit-hello:v1) to the ACR using docker tag and docker push.
Provider Registration: Registered the Microsoft.ContainerInstance resource provider for the subscription using az provider register (a one-time setup step).
ACI Creation (with Credentials & Identity): Created the Azure Container Instance (streamlit-hello-app) using az container create. We specified:
The image from our ACR.
ACR admin credentials (--registry-username, --registry-password) to allow the initial pull.
A system-assigned managed identity (--assign-identity) for secure access going forward.
Required parameters like --os-type Linux, --cpu, --memory, --ports 8501, and --ip-address Public.
Role Assignment: Granted the ACI's new system-assigned managed identity the AcrPull role on the ACR using az role assignment create. This allows the ACI to pull images using its identity in the future (e.g., on restarts) without needing the admin credentials embedded.
ACI Stop: Stopped the running ACI instance to conserve costs using az container stop.