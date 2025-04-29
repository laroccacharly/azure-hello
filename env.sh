export APP_NAME="azure-hello"
export CONTAINER_NAME="$APP_NAME-container"
export DOCKER_DEFAULT_PLATFORM=linux/amd64

export ACR_NAME="helloacr04042025"
export RESOURCE_GROUP_NAME="hello-rg-04042025"
export IMAGE_NAME="$ACR_NAME.azurecr.io/$APP_NAME"
export INSTANCE_NAME="${APP_NAME}-aci-cli"

# SQL Configuration
export SQL_SERVER_NAME="${APP_NAME}-sql-server"
export SQL_DB_NAME="${APP_NAME}_db"
export SQL_ADMIN="azureuser"
export SQL_TIER="Basic"  # Options: Basic, Standard, Premium, GeneralPurpose, BusinessCritical, Hyperscale

# Key Vault Configuration
export KEYVAULT_NAME="${APP_NAME}-key"

alias login="az acr login --name $ACR_NAME"

alias build="docker build -t $IMAGE_NAME ."
alias run="echo "http://localhost:8501" && docker run --name $CONTAINER_NAME -p 8501:8501 -v $(pwd)/src:/app/src $IMAGE_NAME"
alias start="echo "http://localhost:8501" && docker start -a $CONTAINER_NAME"
alias stop="docker stop $CONTAINER_NAME"
alias reload="docker restart $CONTAINER_NAME"
alias push="docker push $IMAGE_NAME"

alias password="az acr credential show --name $ACR_NAME --query passwords"

# Instance Management
alias list_instances='az container list --resource-group $RESOURCE_GROUP_NAME --output table'
alias stop_instance='az container stop --name $INSTANCE_NAME --resource-group $RESOURCE_GROUP_NAME'

# Key Vault Management
alias check_keyvault='az provider show -n Microsoft.KeyVault --query registrationState -o tsv'

alias await_check_keyvault='while [[ "$(check_keyvault)" != "Registered" ]]; do \
    echo "Current status: $(check_keyvault). Waiting..." && \
    sleep 10; \
done && \
echo "KeyVault provider is now registered!"'

alias register_keyvault='az provider register --namespace Microsoft.KeyVault && \
echo "Waiting for registration..." && \
await_check_keyvault'

# SQL Provider Management
alias check_sql_provider='az provider show -n Microsoft.Sql --query registrationState -o tsv'

alias await_check_sql_provider='while [[ "$(check_sql_provider)" != "Registered" ]]; do \
    echo "Current status: $(check_sql_provider). Waiting..." && \
    sleep 10; \
done && \
echo "SQL provider is now registered!"'

alias register_sql_provider='az provider register --namespace Microsoft.Sql && \
echo "Waiting for registration..." && \
await_check_sql_provider'

# Simplified Key Vault setup - all in one command
alias create_keyvault='
az keyvault create \
--name $KEYVAULT_NAME \
--resource-group $RESOURCE_GROUP_NAME \
--location eastus \
--sku standard \
--enable-rbac-authorization true \
--output table'

alias set_permissions='az keyvault set-policy --name $KEYVAULT_NAME --resource-group $RESOURCE_GROUP_NAME --object-id $(az ad signed-in-user show --query id -o tsv) --secret-permissions get list set delete --output table'

alias create_sql_secret='SQL_PASSWORD=$(openssl rand -base64 32) && \
echo "$SQL_PASSWORD" | az keyvault secret set \
--vault-name $KEYVAULT_NAME \
--name "${SQL_SERVER_NAME}-password" \
--value "@-" \
--output table && \
echo "SQL password stored in Key Vault as: ${SQL_SERVER_NAME}-password"'

alias set_secret='az keyvault secret set \
--vault-name $KEYVAULT_NAME \
--name'  # Usage: set_secret secret-name secret-value

alias get_secret='az keyvault secret show \
--vault-name $KEYVAULT_NAME \
--name'  # Usage: get_secret secret-name

alias list_secrets='az keyvault secret list \
--vault-name $KEYVAULT_NAME \
--output table'

# Modified SQL server creation to store password in Key Vault
alias create_sql_server='SQL_PASSWORD=$(az keyvault secret show \
--vault-name $KEYVAULT_NAME \
--name "${SQL_SERVER_NAME}-password" \
--query value -o tsv) && \
az sql server create \
--name $SQL_SERVER_NAME \
--resource-group $RESOURCE_GROUP_NAME \
--location centralus \
--admin-user $SQL_ADMIN \
--admin-password "$SQL_PASSWORD" \
--output table'

alias create_firewall_rule='
az sql server firewall-rule create \
--name AllowAllIps \
--resource-group $RESOURCE_GROUP_NAME \
--server $SQL_SERVER_NAME \
--start-ip-address 0.0.0.0 \
--end-ip-address 255.255.255.255 \
--output table'

alias create_sql_db='az sql db create \
--resource-group $RESOURCE_GROUP_NAME \
--server $SQL_SERVER_NAME \
--name $SQL_DB_NAME \
--tier $SQL_TIER \
--output table'

alias deploy='az container create \
--resource-group $RESOURCE_GROUP_NAME \
--name $INSTANCE_NAME \
--image ${IMAGE_NAME}:latest \
--dns-name-label ${APP_NAME}-cli-$(openssl rand -hex 4) \
--ports 8501 \
--os-type Linux \
--registry-username $ACR_NAME \
--cpu 1 --memory 1.5'