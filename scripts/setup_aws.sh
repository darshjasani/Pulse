#!/bin/bash

# Setup AWS resources for Pulse

set -e

echo "☁️  Setting up AWS resources for Pulse..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first:"
    echo "   https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Run 'aws configure' first."
    exit 1
fi

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}

echo "✅ AWS Account: $AWS_ACCOUNT_ID"
echo "✅ AWS Region: $AWS_REGION"

# Create SQS queue
echo ""
echo "📬 Creating SQS queue..."
QUEUE_NAME="pulse-post-created"

QUEUE_URL=$(aws sqs create-queue \
    --queue-name $QUEUE_NAME \
    --region $AWS_REGION \
    --query 'QueueUrl' \
    --output text 2>/dev/null || \
    aws sqs get-queue-url \
    --queue-name $QUEUE_NAME \
    --region $AWS_REGION \
    --query 'QueueUrl' \
    --output text)

echo "✅ SQS Queue URL: $QUEUE_URL"

# Update .env file with AWS configuration
echo ""
echo "📝 Updating .env with AWS configuration..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|SQS_QUEUE_URL=.*|SQS_QUEUE_URL=$QUEUE_URL|" .env
    sed -i '' "s|AWS_REGION=.*|AWS_REGION=$AWS_REGION|" .env
else
    # Linux
    sed -i "s|SQS_QUEUE_URL=.*|SQS_QUEUE_URL=$QUEUE_URL|" .env
    sed -i "s|AWS_REGION=.*|AWS_REGION=$AWS_REGION|" .env
fi

echo "✅ .env file updated"

echo ""
echo "✅ AWS setup complete!"
echo ""
echo "📋 Created resources:"
echo "  - SQS Queue: $QUEUE_NAME"
echo ""
echo "⚠️  IMPORTANT: Update your .env file with:"
echo "  - AWS_ACCESS_KEY_ID"
echo "  - AWS_SECRET_ACCESS_KEY"
echo ""
echo "💡 Optional: Set up RDS (PostgreSQL) for production database"
echo ""

