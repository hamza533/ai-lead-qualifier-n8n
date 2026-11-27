// LeadPilot production profile: n8n in queue mode on Azure Container Apps.
//
//   n8n-main    editor, webhooks, forms, triggers; enqueues executions (1 replica)
//   n8n-worker  runs executions from the Redis queue; scales on CPU (1..maxWorkers)
//   runners     task-runner sidecar in both apps (Code nodes run here, not in n8n)
//   Postgres    Flexible Server: n8n database + leadpilot database (leads ledger)
//   Redis       Azure Cache for Redis: the queue
//   Key Vault   every secret; apps read it through a user-assigned managed identity
//   Files       Azure Files share mounted read-only at /home/node/.n8n-files/config
//   Logs        Log Analytics + Application Insights (JSON logs from all containers)
//
// Validate: az bicep build --file deploy/azure/main.bicep
// Deploy:   see deploy/azure/README.md (the GitHub deploy workflow is disabled by default)

targetScope = 'resourceGroup'

@description('Short name used in every resource name, e.g. leadpilot.')
@minLength(3)
@maxLength(12)
param prefix string = 'leadpilot'

@description('Azure region.')
param location string = resourceGroup().location

@description('Pinned n8n version; must match docker-compose.yml.')
param n8nVersion string = '2.49.6'

@description('Public host name for the editor, forms and webhooks (custom domain), or empty to use the Container Apps default domain.')
param publicHost string = ''

@description('PostgreSQL administrator login.')
param postgresAdminLogin string = 'leadpilotadmin'

@description('PostgreSQL administrator password (stored in Key Vault, used by both databases).')
@secure()
param postgresAdminPassword string

@description('Postgres SKU: Burstable B1ms fits ~500 leads/month; B2s or GP_Standard_D2ds_v5 for more.')
param postgresSku string = 'Standard_B1ms'

@description('Postgres SKU tier matching postgresSku.')
@allowed(['Burstable', 'GeneralPurpose'])
param postgresTier string = 'Burstable'

@description('Redis SKU: Basic has no SLA; use Standard for production.')
@allowed(['Basic', 'Standard'])
param redisSku string = 'Standard'

@description('Maximum worker replicas.')
@minValue(1)
@maxValue(10)
param maxWorkers int = 3

@description('Object ID of the person or group that manages secrets in Key Vault.')
param keyVaultAdminObjectId string

@description('First deployment only: create the app secrets with the value "set-me" so the apps can start. Leave false afterwards, or every deployment would reset them.')
param createPlaceholderSecrets bool = false

@description('Slack channel ID for approval requests and the cold-lead digest.')
param slackApprovalChannel string

@description('Slack channel ID for failure and warning alerts.')
param slackAlertsChannel string

@description('Sender of approved replies, e.g. "Northwind Digital <hello@northwind.example>".')
param emailFrom string

@description('Booking link included in every reply draft.')
param bookingLink string

@description('Address space of the virtual network (Container Apps + private Postgres).')
param vnetAddressPrefix string = '10.40.0.0/16'

var name = toLower(prefix)
var suffix = uniqueString(resourceGroup().id)
var kvName = '${name}-kv-${take(suffix, 6)}'
var tags = { app: 'leadpilot', managedBy: 'bicep' }

// ---------------------------------------------------------------------------------------------
// Monitoring
// ---------------------------------------------------------------------------------------------
resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${name}-logs'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${name}-insights'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logs.id
  }
}

// ---------------------------------------------------------------------------------------------
// Identity + Key Vault
// ---------------------------------------------------------------------------------------------
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${name}-identity'
  location: location
  tags: tags
}

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: kvName
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 30
    enablePurgeProtection: true
    publicNetworkAccess: 'Enabled'
  }
}

var kvSecretsUser = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
var kvSecretsOfficer = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7')

resource appReadsSecrets 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, identity.id, kvSecretsUser)
  scope: vault
  properties: {
    roleDefinitionId: kvSecretsUser
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource adminManagesSecrets 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, keyVaultAdminObjectId, kvSecretsOfficer)
  scope: vault
  properties: {
    roleDefinitionId: kvSecretsOfficer
    principalId: keyVaultAdminObjectId
  }
}

// Secrets the apps read. Their real values are set by an operator in Key Vault (see
// deploy/azure/README.md); the template never writes them, so a redeploy can't reset them.
// Only on the very first deployment (createPlaceholderSecrets=true) are placeholders created,
// so the apps can start before the operator has set the values.
var operatorSecrets = [
  'n8n-encryption-key'
  'n8n-runners-auth-token'
  'webhook-hmac-secret'
]

resource secrets 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = [for s in operatorSecrets: if (createPlaceholderSecrets) {
  parent: vault
  name: s
  properties: {
    value: 'set-me'
    attributes: { enabled: true }
  }
}]

resource dbPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'postgres-password'
  properties: { value: postgresAdminPassword }
}

// ---------------------------------------------------------------------------------------------
// Network: Container Apps and a private Postgres in one VNet (no public database endpoint)
// ---------------------------------------------------------------------------------------------
resource vnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {
  name: '${name}-vnet'
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: [vnetAddressPrefix] }
    subnets: [
      {
        name: 'apps'
        properties: {
          addressPrefix: cidrSubnet(vnetAddressPrefix, 23, 0)
          delegations: [{ name: 'apps', properties: { serviceName: 'Microsoft.App/environments' } }]
        }
      }
      {
        name: 'postgres'
        properties: {
          addressPrefix: cidrSubnet(vnetAddressPrefix, 24, 4)
          delegations: [{ name: 'pg', properties: { serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers' } }]
        }
      }
    ]
  }
}

resource pgDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: '${name}.private.postgres.database.azure.com'
  location: 'global'
  tags: tags
}

resource pgDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: pgDnsZone
  name: '${name}-vnet-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnet.id }
  }
}

// ---------------------------------------------------------------------------------------------
// PostgreSQL Flexible Server (n8n + leadpilot databases), private access only
// ---------------------------------------------------------------------------------------------
resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: '${name}-pg-${take(suffix, 6)}'
  location: location
  tags: tags
  dependsOn: [pgDnsLink]
  sku: { name: postgresSku, tier: postgresTier }
  properties: {
    version: '17'
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: postgresAdminPassword
    storage: { storageSizeGB: 32, autoGrow: 'Enabled' }
    backup: { backupRetentionDays: 14, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
    authConfig: { activeDirectoryAuth: 'Disabled', passwordAuth: 'Enabled' }
    network: {
      delegatedSubnetResourceId: '${vnet.id}/subnets/postgres'
      privateDnsZoneArmResourceId: pgDnsZone.id
      publicNetworkAccess: 'Disabled'
    }
  }
}

resource n8nDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: 'n8n'
  properties: { charset: 'UTF8', collation: 'en_US.utf8' }
}

resource leadsDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: 'leadpilot'
  properties: { charset: 'UTF8', collation: 'en_US.utf8' }
}

// ---------------------------------------------------------------------------------------------
// Redis (queue)
// ---------------------------------------------------------------------------------------------
resource redis 'Microsoft.Cache/redis@2024-03-01' = {
  name: '${name}-redis-${take(suffix, 6)}'
  location: location
  tags: tags
  properties: {
    sku: { name: redisSku, family: 'C', capacity: 0 }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    redisConfiguration: { 'maxmemory-policy': 'noeviction' }
  }
}

resource redisKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'redis-password'
  properties: { value: redis.listKeys().primaryKey }
}

// ---------------------------------------------------------------------------------------------
// Config share (config/icp.json, config/reply_style.md)
// ---------------------------------------------------------------------------------------------
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: '${take(replace(name, '-', ''), 10)}cfg${take(suffix, 8)}'
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource configShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileService
  name: 'config'
  properties: { shareQuota: 1 }
}

// ---------------------------------------------------------------------------------------------
// Container Apps
// ---------------------------------------------------------------------------------------------
resource appEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${name}-env'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
    daprAIConnectionString: insights.properties.ConnectionString
    vnetConfiguration: {
      infrastructureSubnetId: '${vnet.id}/subnets/apps'
      internal: false
    }
    workloadProfiles: [{ name: 'Consumption', workloadProfileType: 'Consumption' }]
  }
}

resource envConfigStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: appEnv
  name: 'config'
  properties: {
    azureFile: {
      accountName: storage.name
      accountKey: storage.listKeys().keys[0].value
      shareName: configShare.name
      accessMode: 'ReadOnly'
    }
  }
}

var host = empty(publicHost) ? '${name}-main.${appEnv.properties.defaultDomain}' : publicHost
// Built from the name (known at the start of the deployment) rather than vault.properties.
var kvUri = 'https://${kvName}${environment().suffixes.keyvaultDns}/'

// Every secret the apps need, read from Key Vault through the managed identity. API keys for
// Gemini, Tavily, HubSpot, Slack and SMTP are not here: they live in n8n credentials,
// encrypted with n8n-encryption-key.
var appSecrets = [for s in concat(operatorSecrets, ['postgres-password', 'redis-password']): {
  name: s
  keyVaultUrl: '${kvUri}secrets/${s}'
  identity: identity.id
}]

// n8n's own secrets are mounted as files (n8n reads *_FILE variables), so workflow
// expressions, which can read the environment, never see them.
var secretsDir = '/mnt/secrets'
var sharedEnv = [
  { name: 'N8N_ENCRYPTION_KEY_FILE', value: '${secretsDir}/n8n-encryption-key' }
  { name: 'DB_TYPE', value: 'postgresdb' }
  { name: 'DB_POSTGRESDB_HOST', value: postgres.properties.fullyQualifiedDomainName }
  { name: 'DB_POSTGRESDB_PORT', value: '5432' }
  { name: 'DB_POSTGRESDB_DATABASE', value: 'n8n' }
  { name: 'DB_POSTGRESDB_USER', value: postgresAdminLogin }
  { name: 'DB_POSTGRESDB_PASSWORD_FILE', value: '${secretsDir}/postgres-password' }
  { name: 'DB_POSTGRESDB_SSL_ENABLED', value: 'true' }
  { name: 'EXECUTIONS_MODE', value: 'queue' }
  { name: 'QUEUE_BULL_REDIS_HOST', value: redis.properties.hostName }
  { name: 'QUEUE_BULL_REDIS_PORT', value: '6380' }
  { name: 'QUEUE_BULL_REDIS_TLS', value: 'true' }
  { name: 'QUEUE_BULL_REDIS_PASSWORD_FILE', value: '${secretsDir}/redis-password' }
  { name: 'QUEUE_HEALTH_CHECK_ACTIVE', value: 'true' }
  { name: 'N8N_RUNNERS_MODE', value: 'external' }
  { name: 'N8N_RUNNERS_AUTH_TOKEN_FILE', value: '${secretsDir}/n8n-runners-auth-token' }
  { name: 'N8N_RUNNERS_BROKER_LISTEN_ADDRESS', value: '0.0.0.0' }
  { name: 'N8N_BLOCK_ENV_ACCESS_IN_NODE', value: 'false' }
  { name: 'N8N_RESTRICT_FILE_ACCESS_TO', value: '/home/node/.n8n-files' }
  { name: 'N8N_HOST', value: host }
  { name: 'N8N_PROTOCOL', value: 'https' }
  { name: 'N8N_WEBHOOK_URL', value: 'https://${host}/' }
  { name: 'N8N_SECURE_COOKIE', value: 'true' }
  { name: 'N8N_LOG_FORMAT', value: 'json' }
  { name: 'N8N_DIAGNOSTICS_ENABLED', value: 'false' }
  { name: 'EXECUTIONS_DATA_PRUNE', value: 'true' }
  { name: 'EXECUTIONS_DATA_MAX_AGE', value: '336' }
  { name: 'GENERIC_TIMEZONE', value: 'Europe/London' }
  // Workflow settings (non-secret)
  { name: 'GEMINI_BASE_URL', value: 'https://generativelanguage.googleapis.com' }
  { name: 'LLM_MODEL', value: 'gemini-3.5-flash' }
  { name: 'TAVILY_BASE_URL', value: 'https://api.tavily.com' }
  { name: 'HUBSPOT_BASE_URL', value: 'https://api.hubapi.com' }
  { name: 'SLACK_BASE_URL', value: 'https://slack.com/api' }
  { name: 'LEADPILOT_DB_NAME', value: 'leadpilot' }
  { name: 'LEAD_RETENTION_DAYS', value: '30' }
  { name: 'FOLLOW_UP_DAYS', value: '3' }
  { name: 'APPROVAL_TIMEOUT_HOURS', value: '24' }
  { name: 'APPROVAL_REMINDER_HOURS', value: '4' }
  { name: 'SLACK_APPROVAL_CHANNEL', value: slackApprovalChannel }
  { name: 'SLACK_ALERTS_CHANNEL', value: slackAlertsChannel }
  { name: 'EMAIL_FROM', value: emailFrom }
  { name: 'BOOKING_LINK', value: bookingLink }
  { name: 'DEMO_MODE', value: 'false' }
  { name: 'DEMO_EMAIL_ALLOWLIST', value: '' }
  { name: 'DRY_RUN', value: 'false' }
  { name: 'EVAL_AUTO_APPROVE', value: 'false' }
  { name: 'WEBHOOK_HMAC_SECRET', secretRef: 'webhook-hmac-secret' }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: insights.properties.ConnectionString }
]

var runnerSidecar = {
  name: 'runners'
  image: 'docker.io/n8nio/runners:${n8nVersion}'
  resources: { cpu: json('0.25'), memory: '0.5Gi' }
  env: [
    { name: 'N8N_RUNNERS_TASK_BROKER_URI', value: 'http://localhost:5679' }
    { name: 'N8N_RUNNERS_AUTH_TOKEN', secretRef: 'n8n-runners-auth-token' }
    { name: 'NODE_FUNCTION_ALLOW_BUILTIN', value: 'crypto' }
  ]
}

var configVolume = { volumeName: 'config', mountPath: '/home/node/.n8n-files/config' }
var secretsVolume = { volumeName: 'secrets', mountPath: secretsDir }

resource main 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${name}-main'
  location: location
  tags: tags
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  dependsOn: [appReadsSecrets, secrets, dbPasswordSecret, redisKeySecret, n8nDb, leadsDb]
  properties: {
    managedEnvironmentId: appEnv.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: appSecrets
      ingress: {
        external: true
        targetPort: 5678
        transport: 'http'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name: 'n8n'
          image: 'docker.io/n8nio/n8n:${n8nVersion}'
          resources: { cpu: json('1.0'), memory: '2Gi' }
          env: sharedEnv
          volumeMounts: [configVolume, secretsVolume]
          probes: [
            { type: 'Liveness', httpGet: { path: '/healthz', port: 5678 }, periodSeconds: 30 }
            { type: 'Readiness', httpGet: { path: '/healthz/readiness', port: 5678 }, periodSeconds: 10 }
          ]
        }
        runnerSidecar
      ]
      volumes: [
        { name: 'config', storageType: 'AzureFile', storageName: envConfigStorage.name }
        { name: 'secrets', storageType: 'Secret' }
      ]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}

resource worker 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${name}-worker'
  location: location
  tags: tags
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  dependsOn: [main]
  properties: {
    managedEnvironmentId: appEnv.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: appSecrets
    }
    template: {
      containers: [
        {
          name: 'n8n-worker'
          image: 'docker.io/n8nio/n8n:${n8nVersion}'
          command: ['n8n', 'worker']
          resources: { cpu: json('1.0'), memory: '2Gi' }
          env: sharedEnv
          volumeMounts: [configVolume, secretsVolume]
        }
        runnerSidecar
      ]
      volumes: [
        { name: 'config', storageType: 'AzureFile', storageName: envConfigStorage.name }
        { name: 'secrets', storageType: 'Secret' }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: maxWorkers
        rules: [{ name: 'cpu', custom: { type: 'cpu', metadata: { type: 'Utilization', value: '70' } } }]
      }
    }
  }
}

output editorUrl string = 'https://${host}/'
output keyVaultName string = vault.name
output postgresHost string = postgres.properties.fullyQualifiedDomainName
output configShare string = '${storage.name}/${configShare.name}'
