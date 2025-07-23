"""Parameter Store helper for retrieving configuration values."""

import os
import boto3
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class ParameterStore:
    def __init__(self):
        self.ssm = boto3.client('ssm')
        self.environment = os.getenv('ENVIRONMENT', 'dev')
    
    @lru_cache(maxsize=100)
    def get_parameter(self, name: str, default: str = None) -> str:
        """Get parameter from Parameter Store with caching."""
        try:
            # Try Parameter Store first using your existing structure
            parameter_name = f"/env/{self.environment}/data-reports/{name}"
            response = self.ssm.get_parameter(Name=parameter_name, WithDecryption=True)
            return response['Parameter']['Value']
        except self.ssm.exceptions.ParameterNotFound:
            logger.warning(f"Parameter not found: {parameter_name}")
        except Exception as e:
            logger.error(f"Error retrieving parameter {parameter_name}: {e}")
        
        # Fall back to environment variable
        env_value = os.getenv(name, default)
        if env_value is None:
            raise ValueError(f"Parameter {name} not found in Parameter Store or environment")
        
        return env_value

# Global instance
parameter_store = ParameterStore()