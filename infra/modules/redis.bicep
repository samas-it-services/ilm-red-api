// modules/redis.bicep - Azure Cache for Redis
//
// Creates a Basic C0 Redis cache (cheapest option ~$16/month).
// Provides 250MB cache for session management, rate limiting, and caching.
//

@description('Redis cache name')
param name string

@description('Azure region')
param location string

@description('Resource tags')
param tags object = {}

// Redis Cache - Basic C0 (cheapest)
resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'Basic'
      family: 'C'
      capacity: 0  // C0 = 250MB, ~$16/month
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    redisConfiguration: {
      'maxmemory-policy': 'volatile-lru'  // Evict keys with TTL when memory full
    }
  }
}

@description('Redis hostname')
output hostname string = redis.properties.hostName

@description('Redis SSL port')
output sslPort int = redis.properties.sslPort

@description('Redis primary key')
output primaryKey string = redis.listKeys().primaryKey

@description('Redis connection string')
output connectionString string = 'rediss://:${redis.listKeys().primaryKey}@${redis.properties.hostName}:${redis.properties.sslPort}'

@description('Redis resource name')
output name string = redis.name
