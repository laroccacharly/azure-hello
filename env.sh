export APP_NAME="azure-hello"
export CONTAINER_NAME="$APP_NAME-container"
export DOCKER_DEFAULT_PLATFORM=linux/amd64

export ACR_NAME="helloacr04042025"
export RESOURCE_GROUP_NAME="hello-rg-04042025"
export IMAGE_NAME="$ACR_NAME.azurecr.io/$APP_NAME"
export INSTANCE_NAME="${APP_NAME}-aci-cli"

alias login="az acr login --name $ACR_NAME"

alias build="docker build -t $IMAGE_NAME ."
alias run="echo "http://localhost:8501" && docker run --name $CONTAINER_NAME -p 8501:8501 -v $(pwd)/src:/app/src $IMAGE_NAME"
alias start="echo "http://localhost:8501" && docker start -a $CONTAINER_NAME"
alias stop="docker stop $CONTAINER_NAME"
alias reload="docker restart $CONTAINER_NAME"
alias push="docker push $IMAGE_NAME"

alias password="az acr credential show --name $ACR_NAME --query passwords"

alias list_instances="az container list --resource-group $RESOURCE_GROUP_NAME --output table"

alias stop_instance="az container stop --name $INSTANCE_NAME --resource-group $RESOURCE_GROUP_NAME"

alias deploy="az container create \
--resource-group $RESOURCE_GROUP_NAME \
--name $INSTANCE_NAME \
--image ${IMAGE_NAME}:latest \
--dns-name-label ${APP_NAME}-cli-$(openssl rand -hex 4) \
--ports 8501 \
--os-type Linux \
--registry-username $ACR_NAME \
--cpu 1 --memory 1.5"