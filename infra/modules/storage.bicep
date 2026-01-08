// modules/storage.bicep - Azure Blob Storage
//
// Creates a Standard LRS storage account for book files.
// Most cost-effective option (~$2-5/month depending on usage).
//

@description('Storage account name (must be globally unique, no hyphens)')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object = {}

@description('Blob container name for books')
param containerName string = 'books'

// Storage Account - Standard LRS (cheapest)
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'  // Locally redundant - cheapest
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false  // Require SAS tokens for access
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    networkAcls: {
      defaultAction: 'Allow'  // Allow all networks (restrict for production)
    }
  }
}

// Blob service
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    cors: {
      corsRules: [
        {
          allowedOrigins: ['*']  // Update for production
          allowedMethods: ['GET', 'HEAD', 'OPTIONS']
          allowedHeaders: ['*']
          exposedHeaders: ['*']
          maxAgeInSeconds: 3600
        }
      ]
    }
  }
}

// Container for books
resource booksContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: containerName
  properties: {
    publicAccess: 'None'  // Private - require SAS tokens
  }
}

@description('Storage account name')
output name string = storageAccount.name

@description('Storage account primary endpoint')
output primaryEndpoint string = storageAccount.properties.primaryEndpoints.blob

@description('Storage account connection string')
output connectionString string = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'

@description('Container URL')
output containerUrl string = '${storageAccount.properties.primaryEndpoints.blob}${containerName}'
