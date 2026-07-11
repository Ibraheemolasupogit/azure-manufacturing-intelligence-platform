// Reference-only Bicep blueprint. Do not deploy for this portfolio milestone.
targetScope = 'resourceGroup'
param location string = 'placeholder-location'
param environmentName string = 'reference'
module storage 'modules/storage.bicep' = { name: 'referenceStorage'; params: { location: location environmentName: environmentName } }
