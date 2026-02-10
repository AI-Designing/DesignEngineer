"""
Custom Exception Hierarchy for AI Designer

Provides a well-structured exception hierarchy for better error handling
and debugging across the application.
"""


class AIDesignerError(Exception):
    """Base exception for all AI Designer errors"""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# Configuration & Initialization Errors
class ConfigurationError(AIDesignerError):
    """Raised when configuration is invalid or missing"""

    pass


class InitializationError(AIDesignerError):
    """Raised when component initialization fails"""

    pass


# FreeCAD Related Errors
class FreeCADError(AIDesignerError):
    """Base class for FreeCAD-related errors"""

    pass


class FreeCADNotFoundError(FreeCADError):
    """Raised when FreeCAD installation cannot be found"""

    pass


class FreeCADExecutionError(FreeCADError):
    """Raised when FreeCAD script execution fails"""

    pass


class FreeCADConnectionError(FreeCADError):
    """Raised when connection to FreeCAD fails"""

    pass


# Script & Code Errors
class ScriptError(AIDesignerError):
    """Base class for script-related errors"""

    pass


class ScriptValidationError(ScriptError):
    """Raised when script validation fails"""

    pass


class ScriptExecutionError(ScriptError):
    """Raised when script execution fails"""

    pass


class ScriptTimeoutError(ScriptError):
    """Raised when script execution times out"""

    pass


# LLM & AI Errors
class LLMError(AIDesignerError):
    """Base class for LLM-related errors"""

    pass


class LLMProviderError(LLMError):
    """Raised when LLM provider encounters an error"""

    pass


class LLMResponseError(LLMError):
    """Raised when LLM response is invalid or malformed"""

    pass


class LLMAPIKeyError(LLMError):
    """Raised when LLM API key is missing or invalid"""

    pass


# Agent Errors
class AgentError(AIDesignerError):
    """Base class for agent-related errors"""

    pass


class AgentExecutionError(AgentError):
    """Raised when agent execution fails"""

    pass


class AgentValidationError(AgentError):
    """Raised when agent validation fails"""

    pass


# State Management Errors
class StateError(AIDesignerError):
    """Base class for state management errors"""

    pass


class StateLoadError(StateError):
    """Raised when state loading fails"""

    pass


class StateSaveError(StateError):
    """Raised when state saving fails"""

    pass


class StateValidationError(StateError):
    """Raised when state validation fails"""

    pass


# Parsing & Validation Errors
class ParseError(AIDesignerError):
    """Base class for parsing errors"""

    pass


class GeometryParseError(ParseError):
    """Raised when geometry parsing fails"""

    pass


class ParameterValidationError(AIDesignerError):
    """Raised when parameter validation fails"""

    pass


# API & Network Errors
class APIError(AIDesignerError):
    """Base class for API-related errors"""

    pass


class APIConnectionError(APIError):
    """Raised when API connection fails"""

    pass


class APIAuthenticationError(APIError):
    """Raised when API authentication fails"""

    pass


class APIRateLimitError(APIError):
    """Raised when API rate limit is exceeded"""

    pass


# Redis & Cache Errors
class CacheError(AIDesignerError):
    """Base class for cache-related errors"""

    pass


class RedisConnectionError(CacheError):
    """Raised when Redis connection fails"""

    pass
