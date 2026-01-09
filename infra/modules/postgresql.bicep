// modules/postgresql.bicep - Azure Database for PostgreSQL Flexible Server
//
// Creates a Burstable B1ms PostgreSQL server with pgvector extension.
// This is the most cost-effective option (~$12/month) with:
// - 1 vCore, 2GB RAM
// - Burst capability for occasional spikes
// - pgvector, uuid-ossp, pg_trgm extensions enabled
//

@description('PostgreSQL server name')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object = {}

@description('Administrator login name')
param administratorLogin string = 'pgadmin'

@description('Administrator password')
@secure()
param administratorPassword string

@description('Database name to create')
param databaseName string = 'ilmred'

// PostgreSQL Flexible Server - Burstable B1ms (cheapest)
resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Standard_B1ms'  // Burstable, 1 vCore, 2GB RAM
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    storage: {
      storageSizeGB: 32  // Minimum storage
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'  // Cost saving
    }
    highAvailability: {
      mode: 'Disabled'  // Cost saving - enable for production
    }
    network: {
      publicNetworkAccess: 'Enabled'  // Required for Container Apps without VNet
    }
  }
}

// Enable required extensions (pgvector, uuid-ossp, pg_trgm)
resource pgExtensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-03-01-preview' = {
  parent: postgres
  name: 'azure.extensions'
  properties: {
    value: 'VECTOR,UUID-OSSP,PG_TRGM'
    source: 'user-override'
  }
}

// Create the application database
resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  parent: postgres
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Firewall rule to allow Azure services
resource firewallRule 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-03-01-preview' = {
  parent: postgres
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Firewall rule to allow all IPs (for development - restrict in production)
resource firewallRuleAll 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-03-01-preview' = {
  parent: postgres
  name: 'AllowAll'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '255.255.255.255'
  }
}

@description('PostgreSQL server FQDN')
output fqdn string = postgres.properties.fullyQualifiedDomainName

@description('PostgreSQL connection string for asyncpg')
output connectionString string = 'postgresql+asyncpg://${administratorLogin}:${administratorPassword}@${postgres.properties.fullyQualifiedDomainName}:5432/${databaseName}?ssl=require'

@description('PostgreSQL server name')
output name string = postgres.name
