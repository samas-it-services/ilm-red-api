// modules/container-registry.bicep - Azure Container Registry
//
// Creates a Basic tier ACR for storing Docker images.
// Basic tier is the most cost-effective option (~$5/month).
//

@description('Container Registry name (must be globally unique, no hyphens)')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object = {}

// Container Registry - Basic tier (cheapest)
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Basic'  // ~$5/month, 10GB storage
  }
  properties: {
    adminUserEnabled: true  // Enable for simple deployments
    publicNetworkAccess: 'Enabled'
    policies: {
      retentionPolicy: {
        status: 'disabled'  // Don't auto-delete untagged images
      }
    }
  }
}

@description('ACR login server (e.g., myacr.azurecr.io)')
output loginServer string = acr.properties.loginServer

@description('ACR resource name')
output name string = acr.name

@description('ACR resource ID')
output id string = acr.id
