# GitHub Secrets Setup Guide

This document explains how to configure GitHub Secrets for automatic deployment to Azure.

## Required Secrets

Add these secrets in your GitHub repository under **Settings > Secrets and variables > Actions**.

### 1. AZURE_CREDENTIALS

Service principal credentials for Azure authentication.

**Create the service principal:**

```bash
# Login to Azure
az login

# Create service principal with Contributor role on the resource group
az ad sp create-for-rbac \
  --name "ilm-red-api-github-actions" \
  --role Contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/ilmred-prod-rg \
  --json-auth
```

**Copy the entire JSON output** and add it as the `AZURE_CREDENTIALS` secret.

Example output format:
```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "subscriptionId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

### 2. Grant ACR Access to Service Principal

The service principal needs push access to the container registry:

```bash
# Get the ACR resource ID
ACR_ID=$(az acr show --name ilmredprodacr --query id --output tsv)

# Grant AcrPush role
az role assignment create \
  --assignee <CLIENT_ID_FROM_ABOVE> \
  --scope $ACR_ID \
  --role AcrPush
```

## Setting Up Secrets in GitHub

1. Go to your repository on GitHub
2. Navigate to **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret**
4. Add the `AZURE_CREDENTIALS` secret with the JSON from the service principal

## Local Development

For local development, use the `infra/parameters.json` file (not tracked in git).

Copy from example:
```bash
cp infra/parameters.example.json infra/parameters.json
```

Edit `parameters.json` and add your API keys locally.

## Workflow Triggers

The deployment workflow triggers on:

- **Push to main**: Automatic deployment
- **Pull request to main**: Run tests only (no deployment)
- **Manual dispatch**: Trigger from GitHub Actions UI

## Verifying Deployment

After a successful deployment, the workflow will output links to:

- API URL
- Health endpoint
- Swagger documentation
- Admin documentation

You can also check the deployment status in the GitHub Actions tab.

## Troubleshooting

### Authentication Failed

If you see authentication errors, verify:
1. The service principal JSON is correctly formatted
2. The service principal has Contributor role on the resource group
3. The service principal has AcrPush role on the container registry

### Container Pull Failed

If the container fails to pull:
1. Verify ACR login credentials
2. Check that the image tag exists in ACR
3. Verify the container app has access to ACR

### Health Check Failed

If health checks fail after deployment:
1. Check container logs: `az containerapp logs show --name ilmred-prod-api --resource-group ilmred-prod-rg`
2. Verify database migrations ran successfully
3. Check environment variables are set correctly

## Security Notes

- Never commit secrets to the repository
- Use GitHub Secrets for all sensitive values
- The `infra/parameters.json` file is in `.gitignore`
- Rotate service principal credentials periodically
