import subprocess
import sys
import os

# --- Configuration ---
# Retrieved from azure_state.py output or Azure portal
ACR_NAME = "helloacr04042025"
# Desired repository name within ACR
REPOSITORY_NAME = "azure-hello"
# Desired tag for the image
IMAGE_TAG = "latest"
# Path to the Dockerfile directory (current directory)
DOCKERFILE_PATH = "."

# Construct the full image name for ACR
ACR_LOGIN_SERVER = f"{ACR_NAME}.azurecr.io"
FULL_IMAGE_NAME = f"{ACR_LOGIN_SERVER}/{REPOSITORY_NAME}:{IMAGE_TAG}"

def run_command(command, description):
    """Runs a shell command and handles errors."""
    print(f"--- Running: {description} ---")
    print(f"$ {' '.join(command)}")
    try:
        # Use shell=False for security and pass command as a list
        process = subprocess.run(command, check=True, text=True, capture_output=True, shell=False)
        print(process.stdout)
        print(f"--- Success: {description} ---\n")
        return True
    except FileNotFoundError:
        print(f"Error: Command '{command[0]}' not found. Is it installed and in your PATH?", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(e.cmd)}", file=sys.stderr)
        print(f"Return code: {e.returncode}", file=sys.stderr)
        print(f"Stderr: {e.stderr.strip()}", file=sys.stderr)
        print(f"Stdout: {e.stdout.strip()}", file=sys.stderr)
        print(f"--- Failed: {description} ---\n", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        print(f"--- Failed: {description} ---\n", file=sys.stderr)
        return False

def push_container():
    """Builds the Docker image and pushes it to ACR."""

    # 1. Login to ACR (Requires Azure CLI login)
    login_command = ["az", "acr", "login", "--name", ACR_NAME]
    if not run_command(login_command, f"Login to ACR: {ACR_NAME}"):
        print("ACR login failed. Please ensure you are logged in with 'az login' and have permissions.", file=sys.stderr)
        sys.exit(1)

    # 2. Build the Docker image
    # Ensure Dockerfile exists
    if not os.path.exists(os.path.join(DOCKERFILE_PATH, 'Dockerfile')):
        print(f"Error: Dockerfile not found in directory '{DOCKERFILE_PATH}'", file=sys.stderr)
        sys.exit(1)

    build_command = ["docker", "build", "-t", FULL_IMAGE_NAME, DOCKERFILE_PATH]
    if not run_command(build_command, f"Build Docker image: {FULL_IMAGE_NAME}"):
        print("Docker build failed.", file=sys.stderr)
        sys.exit(1)

    # 3. Push the Docker image to ACR
    push_command = ["docker", "push", FULL_IMAGE_NAME]
    if not run_command(push_command, f"Push Docker image to {ACR_LOGIN_SERVER}"):
        print("Docker push failed.", file=sys.stderr)
        sys.exit(1)

    print("--- Docker image build and push completed successfully! ---")
    print(f"Image name: {FULL_IMAGE_NAME}")

if __name__ == "__main__":
    push_container() 