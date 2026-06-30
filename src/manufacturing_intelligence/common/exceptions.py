"""Platform exception hierarchy."""


class ManufacturingIntelligenceError(Exception):
    """Base exception for platform-specific errors."""


class ConfigurationError(ManufacturingIntelligenceError):
    """Raised when configuration is missing, invalid, or unsafe."""


class DataContractError(ManufacturingIntelligenceError):
    """Raised when future data contracts are violated."""


class PipelineExecutionError(ManufacturingIntelligenceError):
    """Raised when a pipeline stage cannot complete successfully."""
