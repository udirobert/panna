// Panna — Azure Container Apps: API service (event-driven, autoscaling)
// Deploy with:  ./azure/deploy.sh   (builds, pushes, provisions, prints endpoint)
// Self-contained module: pass environmentName + image, optionally Foundry + frontend params.

@description('Short environment name (lowercase, no hyphens)')
param environmentName string

@description('Region')
param location string = resourceGroup().location

@description('Container image reference (built & pushed by azd, e.g. registry.azurecr.io/panna/api:tag)')
param image string

// Foundry / Azure OpenAI — supplied at deploy via azd config env vars (never committed)
param foundryEndpoint string = ''
param foundryDeployment string = 'gpt-5.4'
param foundryApiVersion string = '2025-03-01-preview'
@secure()
param foundryApiKey string = ''

// Where the shareable case-file poster should point its "replay" button
param frontendOrigin string = ''

var caName = 'panna-${environmentName}'

resource ca 'Microsoft.App/containerApps@2024-03-01' = {
  name: caName
  location: location
  properties:
    workloadProfiles: [
      {
        name: 'default'
        cpu: 1.0
        memory: '2Gi'
      }
    ]
    configuration:
      ingress:
        external: true
        targetPort: 8000
        trafficWeight: [
          {
            latestRevision: true
            weight: 100
          }
        ]
    template:
      containers: [
        {
          name: caName
          image: image
          env: [
            {
              name: 'FOUNDRY_ENDPOINT'
              value: foundryEndpoint
            }
            {
              name: 'FOUNDRY_API_KEY'
              secureRef: { secretName: 'foundryApiKey' }
            }
            {
              name: 'FOUNDRY_DEPLOYMENT'
              value: foundryDeployment
            }
            {
              name: 'FOUNDRY_API_VERSION'
              value: foundryApiVersion
            }
            {
              name: 'FRONTEND_ORIGIN'
              value: frontendOrigin
            }
          ]
          ports: [
            {
              containerPort: 8000
            }
          ]
          resources: {
            cpu: 1.0
            memory: '2Gi'
          }
          probes: [
            {
              type: 'Http'
              periodSeconds: 30
              timeoutSeconds: 3
              path: '/health'
              port: 8000
            }
          ]
        }
      ]
    scalingRules: [
      {
        name: 'httpConcurrency'
        custom: {
          metadata: [
            {
              name: 'type'
              value: 'Http'
            }
            {
              name: 'metadataName'
              value: 'httpConcurrency'
            }
            {
              name: 'target'
              value: '50'
            }
          ]
          authentication: {
            type: 'System'
          }
        }
      }
    ]
}

// Secret for the Foundry API key — value passed in from azd at deploy time
resource secret 'Microsoft.App/containerApps/secrets@2024-03-01' = {
  name: 'foundryApiKey'
  parent: ca
  properties: {
    value: foundryApiKey
  }
}

output apiEndpoint string = ca.properties.ingress.fqdn
output containerAppName string = caName
