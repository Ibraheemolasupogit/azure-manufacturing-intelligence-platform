// Reference-only Bicep module. Do not deploy for this portfolio milestone.
param location string
param environmentName string
var referenceComponent = 'aiServices'
output componentName string = referenceComponent
