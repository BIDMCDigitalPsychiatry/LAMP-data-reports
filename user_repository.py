import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from dynamo_config import config

logger = logging.getLogger(__name__)


class DynamoUser(UserMixin):
    """User model for DynamoDB that maintains Flask-Login compatibility."""
    
    def __init__(self, user_data: dict):
        self.id = user_data.get('Id')
        self.username = user_data.get('Username')
        self.password_hash = user_data.get('passwordHash')
        self.role = user_data.get('role')
        self.site = user_data.get('site')
        self.created_at = user_data.get('createdAt')
        self.updated_at = user_data.get('updatedAt')
        self.last_login_at = user_data.get('lastLoginAt')
        self._is_active = user_data.get('isActive', True)
        self.metadata = user_data.get('metadata', {})
    
    def verify(self, password: str) -> bool:
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        """Return user ID for Flask-Login."""
        return str(self.id)
    
    @property
    def is_active(self):
        """Override UserMixin's is_active property."""
        return self._is_active
    
    def to_dict(self) -> dict:
        """Convert user to DynamoDB item format."""
        item = {
            'Id': self.id,
            'Username': self.username,
            'passwordHash': self.password_hash,
            'role': self.role,
            'createdAt': self.created_at,
            'updatedAt': self.updated_at,
            'isActive': self._is_active
        }
        
        if self.site:
            item['site'] = self.site
        
        if self.last_login_at:
            item['lastLoginAt'] = self.last_login_at
            
        if self.metadata:
            item['metadata'] = self.metadata
            
        return item
    
    def __repr__(self):
        return f"<User {self.username}:{self.role}:{self.site or '-'}>"


class DynamoUserRepository:
    """Repository for user operations in DynamoDB."""
    
    def __init__(self):
        try:
            self.dynamodb = boto3.resource('dynamodb', **config.get_boto3_config())
            self.table = self.dynamodb.Table(config.table_name)
            
            # Log authentication method for debugging
            if config.is_using_iam_role():
                logger.info("Using IAM role for DynamoDB authentication")
            elif config.is_local_development():
                logger.info(f"Using local DynamoDB endpoint: {config.endpoint_url}")
            else:
                logger.info("Using explicit AWS credentials for DynamoDB")
                
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB connection: {e}")
            raise
        
    def create_user(self, username: str, password: str, role: str, site: Optional[str] = None) -> DynamoUser:
        """Create a new user."""
        # Check if username already exists
        if self.get_by_username(username):
            raise ValueError(f"Username {username} already exists")
        
        user_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + 'Z'
        
        item = {
            'Id': user_id,
            'Username': username,
            'passwordHash': generate_password_hash(password),
            'role': role,
            'createdAt': now,
            'updatedAt': now,
            'isActive': True
        }
        
        if site:
            item['site'] = site
            
        try:
            self.table.put_item(Item=item)
            logger.info(f"Created user: {username}")
            return DynamoUser(item)
        except ClientError as e:
            logger.error(f"Error creating user: {e}")
            raise
    
    def get_by_id(self, user_id: str) -> Optional[DynamoUser]:
        """Get user by ID using scan since we only have the ID part of composite key."""
        try:
            # Since we have a composite key (Id + Username) but only know the ID,
            # we need to scan with a filter instead of get_item
            response = self.table.scan(
                FilterExpression='Id = :id AND isActive = :active',
                ExpressionAttributeValues={
                    ':id': user_id,
                    ':active': True
                }
            )
            
            items = response.get('Items', [])
            if items:
                return DynamoUser(items[0])
            return None
        except ClientError as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    def get_by_username(self, username: str) -> Optional[DynamoUser]:
        """Get user by username using GSI."""
        try:
            response = self.table.query(
                IndexName=config.username_index,
                KeyConditionExpression=Key('Username').eq(username)
            )
            
            items = response.get('Items', [])
            # Filter for active users
            for item in items:
                user = DynamoUser(item)
                if user.is_active:
                    return user
            return None
        except ClientError as e:
            logger.error(f"Error getting user by username: {e}")
            return None
    
    def update_password(self, user_id: str, username: str, new_password: str) -> bool:
        """Update user password."""
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            self.table.update_item(
                Key={'Id': user_id, 'Username': username},
                UpdateExpression='SET passwordHash = :hash, updatedAt = :timestamp',
                ExpressionAttributeValues={
                    ':hash': generate_password_hash(new_password),
                    ':timestamp': now
                }
            )
            logger.info(f"Updated password for user: {username}")
            return True
        except ClientError as e:
            logger.error(f"Error updating password: {e}")
            return False
    
    def update_last_login(self, user_id: str, username: str) -> bool:
        """Update last login timestamp."""
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            self.table.update_item(
                Key={'Id': user_id, 'Username': username},
                UpdateExpression='SET lastLoginAt = :timestamp',
                ExpressionAttributeValues={
                    ':timestamp': now
                }
            )
            return True
        except ClientError as e:
            logger.error(f"Error updating last login: {e}")
            return False
    
    def delete_user(self, username: str) -> int:
        """Soft delete user by username."""
        user = self.get_by_username(username)
        if not user:
            return 0
            
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            self.table.update_item(
                Key={'Id': user.id, 'Username': user.username},
                UpdateExpression='SET isActive = :inactive, updatedAt = :timestamp',
                ExpressionAttributeValues={
                    ':inactive': False,
                    ':timestamp': now
                }
            )
            logger.info(f"Soft deleted user: {username}")
            return 1
        except ClientError as e:
            logger.error(f"Error deleting user: {e}")
            return 0
    
    def list_all_users(self) -> List[DynamoUser]:
        """List all active users."""
        try:
            response = self.table.scan()
            items = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response.get('Items', []))
            
            # Filter for active users and convert to DynamoUser objects
            users = []
            for item in items:
                user = DynamoUser(item)
                if user.is_active:
                    users.append(user)
                    
            # Sort by ID to maintain consistency with SQLite behavior
            return sorted(users, key=lambda u: u.id)
        except ClientError as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    def list_users_by_site(self, site: str) -> List[DynamoUser]:
        """List all active users for a specific site."""
        try:
            # Since site is not indexed, we need to scan with a filter
            response = self.table.scan(
                FilterExpression='site = :site AND isActive = :active',
                ExpressionAttributeValues={
                    ':site': site,
                    ':active': True
                }
            )
            
            items = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey'],
                    FilterExpression='site = :site AND isActive = :active',
                    ExpressionAttributeValues={
                        ':site': site,
                        ':active': True
                    }
                )
                items.extend(response.get('Items', []))
            
            users = [DynamoUser(item) for item in items]
            return sorted(users, key=lambda u: u.id)
        except ClientError as e:
            logger.error(f"Error listing users by site: {e}")
            return []