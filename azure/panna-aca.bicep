// Panna — Azure Container Apps: API service (event-driven, autoscaling)
// Deploy with:  ./azure/deploy.sh   (builds, pushes, provisions, prints endpoint)
// Self-contained module: pass environmentName + image, optionally Foundry + frontend params.
//
// Keyless by default — the winners' standard. The container app runs under a
// system-assigned managed identity; when `foundryAccountName` is provided it is
// granted "Cognitive Services OpenAI User" on that account, and the app mints
// Entra tokens at runtime via DefaultAzureCredential. No secrets are stored.

@description('Short environment name (lowercase, no hyphens)')
param environmentName string

@description('Region')
param location string = resourceGroup().location

@description('Container image reference (built & pushed by azd, e.g. registry.azurecr.io/panna/api:tag)')
param image string

// Foundry / Azure OpenAI — endpoint + deployment; auth is the managed identity
param foundryEndpoint string = ''
param foundryDeployment string = 'gpt-5.4'
param foundryApiVersion string = '2025-03-01-preview'

@description('Name of the Azure OpenAI / Foundry account to grant the identity access to (empty = no grant)')
param foundryAccountName string = ''

// Where the shareable case-file poster should point its "replay" button
param frontendOrigin string = ''

// Optional AI-services wiring for the multilingual + spoken feeds. Both
// clients take managed-identity Entra tokens at runtime (TRANSLATOR_AUTH /
// SPEECH_AUTH = entra) — set the region only when the resources exist; left
// empty the API serves the honest fallback (original text / text AD feed).
param translatorRegion string = ''
param translatorAuth string = ''
param speechRegion string = ''
param speechAuth string = ''

@description('Name of the AI-services account hosting Translator/Speech (empty = no grant); Entra auth needs Cognitive Services User on it')
param aiServicesAccountName string = ''

var caName = 'panna-${environmentName}'

// Cognitive Services OpenAI User — lets the identity call chat completions
var openAiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
// Cognitive Services User — lets the identity call Translator + Speech APIs
var cognitiveUserRoleId = 'a97b65f3-24c7-4388-baec-2e87135dc908'

resource ca 'Microsoft.App/containerApps@2024-03-01' = {
  name: caName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
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
            {
              name: 'TRANSLATOR_REGION'
              value: translatorRegion
            }
            {
              name: 'TRANSLATOR_AUTH'
              value: translatorAuth
            }
            {
              name: 'SPEECH_REGION'
              value: speechRegion
            }
            {
              name: 'SPEECH_AUTH'
              value: speechAuth
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

// Grant the app's managed identity OpenAI access on the Foundry account —
// keyless end to end, exactly what the winning submissions standardized on.
resource foundryAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing =
  if (foundryAccountName != '') {
    name: foundryAccountName
  }

resource openAiRole 'Microsoft.Authorization/roleAssignments@2022-04-01' =
  if (foundryAccountName != '') {
    name: guid(foundryAccount.id, ca.id, openAiUserRoleId)
    scope: foundryAccount
    properties: {
      roleDefinitionId: subscriptionResourceId(
        'Microsoft.Authorization/roleDefinitions',
        openAiUserRoleId
      )
      principalId: ca.identity.principalId
      principalType: 'ServicePrincipal'
    }
  }

// Same keyless grant for the AI-services account (Translator/Speech live
// behind one multi-service resource on most subscriptions).
resource aiServicesAccount 'Microsoft.CognitiveServices/accounts@2024-10-01' existing =
  if (aiServicesAccountName != '') {
    name: aiServicesAccountName
  }

resource cognitiveRole 'Microsoft.Authorization/roleAssignments@2022-04-01' =
  if (aiServicesAccountName != '') {
    name: guid(aiServicesAccount.id, ca.id, cognitiveUserRoleId)
    scope: aiServicesAccount
    properties: {
      roleDefinitionId: subscriptionResourceId(
        'Microsoft.Authorization/roleDefinitions',
        cognitiveUserRoleId
      )
      principalId: ca.identity.principalId
      principalType: 'ServicePrincipal'
    }
  }

output apiEndpoint string = ca.properties.ingress.fqdn
output containerAppName string = caName
output principalId string = ca.identity.principalId
