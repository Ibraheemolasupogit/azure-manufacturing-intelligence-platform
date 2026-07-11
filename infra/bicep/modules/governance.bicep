// Reference-only Bicep module. Do not deploy for this portfolio milestone.
param location string
param environmentName string
var referenceComponent = 'governance'
output componentName string = referenceComponent
