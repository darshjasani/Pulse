"""
Fan-out worker - processes post_created events and pushes to follower timelines
"""
import boto3
import json
import time
import logging
from typing import Optional, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.config import settings
from services.models import Follow
from services.redis_client import RedisClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FanoutWorker:
    """
    Worker that processes post_created events from SQS
    and fans out posts to follower timelines in Redis
    """
    
    def __init__(self):
        self.redis_client = RedisClient()
        self.sqs_client: Optional[Any] = None
        self.queue_url = settings.sqs_queue_url
        
        # Database connection
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Initialize SQS if available
        if settings.is_aws_enabled and self.queue_url:
            try:
                self.sqs_client = boto3.client(
                    'sqs',
                    region_name=settings.aws_region,
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                )
                logger.info("SQS client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize SQS: {e}")
                self.sqs_client = None
    
    def get_db(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def process_post_created(self, event: Dict[str, Any]) -> bool:
        """
        Process a post_created event
        Fan out post to all follower timelines
        """
        try:
            post_id = event['post_id']
            author_id = event['author_id']
            is_celebrity = event['is_celebrity']
            timestamp = event['timestamp']
            
            # Skip fan-out for celebrities (they will be pulled at read time)
            if is_celebrity:
                logger.info(f"Skipping fan-out for celebrity post {post_id}")
                return True
            
            # Get all followers from database
            db = self.get_db()
            try:
                followers = db.query(Follow.follower_id).filter(
                    Follow.following_id == author_id
                ).all()
                
                follower_ids = [f[0] for f in followers]
                logger.info(f"Fanning out post {post_id} to {len(follower_ids)} followers")
                
                # Add post to each follower's timeline in Redis
                success_count = 0
                for follower_id in follower_ids:
                    if self.redis_client.add_to_timeline(follower_id, post_id, timestamp):
                        success_count += 1
                
                # Also add to author's own timeline
                self.redis_client.add_to_timeline(author_id, post_id, timestamp)
                
                logger.info(f"Fan-out complete: {success_count}/{len(follower_ids)} successful")
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to process post_created event: {e}", exc_info=True)
            return False
    
    def poll_sqs(self):
        """
        Poll SQS for messages and process them
        """
        if not self.sqs_client or not self.queue_url:
            logger.error("SQS not configured, cannot poll")
            return
        
        logger.info(f"Starting SQS polling from {self.queue_url}")
        
        while True:
            try:
                # Receive messages from SQS
                response = self.sqs_client.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=20,  # Long polling
                    MessageAttributeNames=['All']
                )
                
                messages = response.get('Messages', [])
                
                if not messages:
                    logger.debug("No messages received, continuing poll...")
                    continue
                
                logger.info(f"Received {len(messages)} messages")
                
                for message in messages:
                    try:
                        # Parse message body
                        body = json.loads(message['Body'])
                        
                        # Process the event
                        if body.get('event_type') == 'post_created':
                            success = self.process_post_created(body)
                            
                            if success:
                                # Delete message from queue
                                self.sqs_client.delete_message(
                                    QueueUrl=self.queue_url,
                                    ReceiptHandle=message['ReceiptHandle']
                                )
                                logger.info(f"Message processed and deleted: {message['MessageId']}")
                            else:
                                logger.warning(f"Failed to process message: {message['MessageId']}")
                        else:
                            logger.warning(f"Unknown event type: {body.get('event_type')}")
                            # Delete unknown messages
                            self.sqs_client.delete_message(
                                QueueUrl=self.queue_url,
                                ReceiptHandle=message['ReceiptHandle']
                            )
                    
                    except Exception as e:
                        logger.error(f"Error processing message: {e}", exc_info=True)
            
            except Exception as e:
                logger.error(f"Error polling SQS: {e}", exc_info=True)
                time.sleep(5)  # Wait before retrying
    
    def run_local_mode(self):
        """
        Run in local mode without SQS (for testing)
        Just keeps the worker alive and processes direct Redis writes
        """
        logger.info("Running in local mode (no SQS)")
        logger.info("Worker is ready to process direct timeline writes")
        
        while True:
            time.sleep(10)
            # In local mode, the API writes directly to Redis
            # This worker just keeps the process alive
    
    def run(self):
        """
        Main run method
        """
        logger.info("Fanout worker starting...")
        logger.info(f"Redis available: {self.redis_client.is_available()}")
        logger.info(f"SQS configured: {self.sqs_client is not None}")
        
        if self.sqs_client and self.queue_url:
            # AWS mode - poll SQS
            self.poll_sqs()
        else:
            # Local mode - just stay alive
            self.run_local_mode()


def main():
    """Entry point"""
    worker = FanoutWorker()
    worker.run()


if __name__ == "__main__":
    main()

