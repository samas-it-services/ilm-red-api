// modules/keyvault.bicep - Azure Key Vault
//
// Creates a Key Vault for storing secrets securely.
// Standard tier (~$0.03 per 10,000 operations).
//

@description('Key Vault name')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object = {}

@description('Secrets to create')
param secrets array = []

// Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enabledForDeployment: true
    enabledForTemplateDeployment: true
    enabledForDiskEncryption: false
    enableRbacAuthorization: true  // Use RBAC instead of access policies
    publicNetworkAccess: 'Enabled'
    softDeleteRetentionInDays: 7  // Minimum soft delete
    enableSoftDelete: true
  }
}

// Create secrets
resource keyVaultSecrets 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = [for secret in secrets: {
  parent: keyVault
  name: secret.name
  properties: {
    value: secret.value
    contentType: 'text/plain'
  }
}]

@description('Key Vault name')
output name string = keyVault.name

@description('Key Vault URI')
output uri string = keyVault.properties.vaultUri

@description('Key Vault resource ID')
output id string = keyVault.id
