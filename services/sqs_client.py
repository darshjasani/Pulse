"""
AWS SQS client for event publishing
"""
import boto3
import json
from typing import Dict, Any, Optional
from services.config import settings
import logging

logger = logging.getLogger(__name__)


class SQSClient:
    """SQS client wrapper for publishing events"""
    
    def __init__(self):
        self.client: Optional[Any] = None
        self.queue_url: str = settings.sqs_queue_url
        self._connect()
    
    def _connect(self):
        """Initialize SQS client if AWS is configured"""
        if not settings.is_aws_enabled:
            logger.info("AWS not configured, SQS disabled")
            return
        
        try:
            self.client = boto3.client(
                'sqs',
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
            logger.info("SQS client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize SQS client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if SQS is available"""
        return self.client is not None and bool(self.queue_url)
    
    def publish_post_created(
        self, 
        post_id: int, 
        author_id: int, 
        is_celebrity: bool,
        timestamp: float
    ) -> bool:
        """
        Publish post created event to SQS
        Returns True if successful, False otherwise
        """
        if not self.is_available():
            logger.warning("SQS not available, skipping event publish")
            return False
        
        try:
            message = {
                "event_type": "post_created",
                "post_id": post_id,
                "author_id": author_id,
                "is_celebrity": is_celebrity,
                "timestamp": timestamp,
            }
            
            response = self.client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    'EventType': {
                        'StringValue': 'post_created',
                        'DataType': 'String'
                    }
                }
            )
            
            logger.info(f"Published post_created event: {post_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish SQS message: {e}")
            return False


# Global SQS client instance
sqs_client = SQSClient()

