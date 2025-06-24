import os

class DynamoConfig:
    """Configuration for DynamoDB connection and table settings.
    
    Supports three authentication methods:
    1. IAM Roles (preferred for ECS) - No credentials needed
    2. Environment variables (for local development with real AWS)
    3. Local DynamoDB endpoint (for local development with DynamoDB Local)
    """
    
    def __init__(self):
        # AWS Settings - Only set if provided via environment
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        
        # DynamoDB Settings
        self.table_name = os.getenv("DYNAMODB_TABLE_NAME", "dev-data-reports-users")
        self.endpoint_url = os.getenv("DYNAMODB_ENDPOINT_URL")  # For local development
        
        # Index names  
        self.username_index = "Username-index"
        
    def get_boto3_config(self) -> dict:
        """Get configuration dictionary for boto3 client.
        
        When running on ECS with IAM roles:
        - Only region is needed; boto3 will automatically use the task role
        
        When running locally:
        - Can use explicit credentials or local endpoint
        """
        config = {
            "region_name": self.aws_region
        }
        
        # For local DynamoDB
        if self.endpoint_url:
            config["endpoint_url"] = self.endpoint_url
            
        # Only add credentials if explicitly provided (not needed for IAM roles)
        if self.aws_access_key_id and self.aws_secret_access_key:
            config["aws_access_key_id"] = self.aws_access_key_id
            config["aws_secret_access_key"] = self.aws_secret_access_key
            
        return config
    
    def is_local_development(self) -> bool:
        """Check if running against local DynamoDB."""
        return bool(self.endpoint_url)
    
    def is_using_iam_role(self) -> bool:
        """Check if using IAM role authentication (no explicit credentials)."""
        return not (self.aws_access_key_id or self.aws_secret_access_key or self.endpoint_url)

# Global config instance
config = DynamoConfig()