// Reference-only Bicep module. Do not deploy for this portfolio milestone.
param location string
param environmentName string
var referenceComponent = 'eventHubs'
output componentName string = referenceComponent
