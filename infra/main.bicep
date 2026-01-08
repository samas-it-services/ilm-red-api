// main.bicep - ILM Red API Infrastructure
//
// This template deploys all Azure resources for the ILM Red API:
// - Azure Container Registry
// - Azure Container Apps Environment + App
// - Azure Database for PostgreSQL Flexible Server
// - Azure Cache for Redis
// - Azure Blob Storage
// - Azure Key Vault
//
// Usage:
//   az deployment group create \
//     --resource-group ilmred-prod-rg \
//     --template-file infra/main.bicep \
//     --parameters @infra/parameters.json
//

// ============================================================================
// PARAMETERS
// ============================================================================

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'prod'

@description('Azure region for all resources')
param location string = 'eastus'

@description('PostgreSQL administrator password')
@secure()
param postgresAdminPassword string = newGuid()

@description('JWT secret for authentication')
@secure()
param jwtSecret string

@description('OpenAI API key (optional)')
@secure()
param openaiApiKey string = ''

@description('Anthropic API key (optional)')
@secure()
param anthropicApiKey string = ''

@description('Qwen API key (optional)')
@secure()
param qwenApiKey string = ''

@description('Google AI API key (optional)')
@secure()
param googleApiKey string = ''

@description('xAI API key (optional)')
@secure()
param xaiApiKey string = ''

@description('DeepSeek API key (optional)')
@secure()
param deepseekApiKey string = ''

// ============================================================================
// VARIABLES
// ============================================================================

var resourcePrefix = 'ilmred-${environment}'
var tags = {
  environment: environment
  project: 'ilm-red-api'
  managedBy: 'bicep'
}

// ============================================================================
// MODULES
// ============================================================================

// Container Registry
module acr 'modules/container-registry.bicep' = {
  name: 'acr-deployment'
  params: {
    name: replace('${resourcePrefix}acr', '-', '')  // ACR names can't have hyphens
    location: location
    tags: tags
  }
}

// Storage Account (for book files)
module storage 'modules/storage.bicep' = {
  name: 'storage-deployment'
  params: {
    name: replace('${resourcePrefix}storage', '-', '')  // Storage names can't have hyphens
    location: location
    tags: tags
    containerName: 'books'
  }
}

// Key Vault (for secrets)
module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault-deployment'
  params: {
    name: '${resourcePrefix}-kv'
    location: location
    tags: tags
    secrets: [
      { name: 'jwt-secret', value: jwtSecret }
      { name: 'postgres-password', value: postgresAdminPassword }
      { name: 'openai-api-key', value: openaiApiKey }
      { name: 'anthropic-api-key', value: anthropicApiKey }
      { name: 'qwen-api-key', value: qwenApiKey }
      { name: 'google-api-key', value: googleApiKey }
      { name: 'xai-api-key', value: xaiApiKey }
      { name: 'deepseek-api-key', value: deepseekApiKey }
      { name: 'storage-connection-string', value: storage.outputs.connectionString }
    ]
  }
}

// PostgreSQL Flexible Server
module postgres 'modules/postgresql.bicep' = {
  name: 'postgres-deployment'
  params: {
    name: '${resourcePrefix}-postgres'
    location: location
    tags: tags
    administratorLogin: 'pgadmin'
    administratorPassword: postgresAdminPassword
    databaseName: 'ilmred'
  }
}

// Redis Cache
module redis 'modules/redis.bicep' = {
  name: 'redis-deployment'
  params: {
    name: '${resourcePrefix}-redis'
    location: location
    tags: tags
  }
}

// Container Apps Environment and App
module containerApps 'modules/container-apps.bicep' = {
  name: 'container-apps-deployment'
  params: {
    environmentName: '${resourcePrefix}-env'
    appName: '${resourcePrefix}-api'
    location: location
    tags: tags
    acrLoginServer: acr.outputs.loginServer
    acrName: acr.outputs.name
    // Environment variables
    environmentVariables: [
      { name: 'ENVIRONMENT', value: 'production' }
      { name: 'DEBUG', value: 'false' }
      { name: 'DATABASE_URL', value: postgres.outputs.connectionString }
      { name: 'REDIS_URL', value: redis.outputs.connectionString }
      { name: 'STORAGE_TYPE', value: 'azure' }
      { name: 'AZURE_STORAGE_CONNECTION_STRING', secretRef: 'storage-connection-string' }
      { name: 'AZURE_STORAGE_CONTAINER', value: 'books' }
      { name: 'JWT_SECRET', secretRef: 'jwt-secret' }
      { name: 'OPENAI_API_KEY', secretRef: 'openai-api-key' }
      { name: 'ANTHROPIC_API_KEY', secretRef: 'anthropic-api-key' }
      { name: 'QWEN_API_KEY', secretRef: 'qwen-api-key' }
      { name: 'GOOGLE_API_KEY', secretRef: 'google-api-key' }
      { name: 'XAI_API_KEY', secretRef: 'xai-api-key' }
      { name: 'DEEPSEEK_API_KEY', secretRef: 'deepseek-api-key' }
      { name: 'AI_DEFAULT_MODEL_PUBLIC', value: 'qwen-turbo' }
      { name: 'AI_DEFAULT_MODEL_PRIVATE', value: 'gpt-4o-mini' }
      { name: 'CORS_ORIGINS', value: '*' }  // Update for production
    ]
    secrets: [
      { name: 'jwt-secret', value: jwtSecret }
      { name: 'storage-connection-string', value: storage.outputs.connectionString }
      { name: 'openai-api-key', value: openaiApiKey }
      { name: 'anthropic-api-key', value: anthropicApiKey }
      { name: 'qwen-api-key', value: qwenApiKey }
      { name: 'google-api-key', value: googleApiKey }
      { name: 'xai-api-key', value: xaiApiKey }
      { name: 'deepseek-api-key', value: deepseekApiKey }
    ]
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Azure Container Registry login server')
output acrLoginServer string = acr.outputs.loginServer

@description('API URL')
output apiUrl string = containerApps.outputs.fqdn

@description('PostgreSQL server FQDN')
output postgresHost string = postgres.outputs.fqdn

@description('Redis hostname')
output redisHost string = redis.outputs.hostname

@description('Storage account name')
output storageAccountName string = storage.outputs.name

@description('Key Vault name')
output keyVaultName string = keyVault.outputs.name

@description('Resource Group')
output resourceGroup string = resourceGroup().name
