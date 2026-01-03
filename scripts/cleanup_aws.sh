#!/bin/bash

# Cleanup AWS resources

set -e

echo "🧹 Cleaning up AWS resources..."

AWS_REGION=${AWS_REGION:-us-east-1}
QUEUE_NAME="pulse-post-created"

# Delete SQS queue
echo "Deleting SQS queue: $QUEUE_NAME"
QUEUE_URL=$(aws sqs get-queue-url \
    --queue-name $QUEUE_NAME \
    --region $AWS_REGION \
    --query 'QueueUrl' \
    --output text 2>/dev/null || echo "")

if [ -n "$QUEUE_URL" ]; then
    aws sqs delete-queue --queue-url $QUEUE_URL --region $AWS_REGION
    echo "✅ SQS queue deleted"
else
    echo "⚠️  SQS queue not found"
fi

echo ""
echo "✅ Cleanup complete!"

