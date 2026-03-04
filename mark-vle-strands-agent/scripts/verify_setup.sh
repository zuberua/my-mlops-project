#!/bin/bash

##############################################################################
# Mark Vle Agent - Setup Verification Script
# 
# Verifies that all components are properly configured and accessible
##############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_header() {
    echo ""
    echo -e "${BLUE}=========================================="
    echo -e "$1"
    echo -e "==========================================${NC}"
}

print_check() {
    echo -e "${YELLOW}Checking: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Load environment variables
if [ -f "$PROJECT_ROOT/config/.env" ]; then
    export $(cat "$PROJECT_ROOT/config/.env" | grep -v '^#' | xargs)
    print_success "Loaded config/.env"
else
    print_warning "config/.env not found"
fi

print_header "Mark Vle Agent - Setup Verification"

# Check 1: AWS CLI
print_check "AWS CLI"
if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version 2>&1 | cut -d' ' -f1)
    print_success "AWS CLI installed: $AWS_VERSION"
else
    print_error "AWS CLI not installed"
    exit 1
fi

# Check 2: Python
print_check "Python"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_success "$PYTHON_VERSION"
else
    print_error "Python 3 not installed"
    exit 1
fi

# Check 3: AWS Credentials
print_check "AWS Credentials"
AWS_PROFILE=${AWS_PROFILE:-default}
if aws sts get-caller-identity --profile "$AWS_PROFILE" &> /dev/null; then
    ACCOUNT_ID=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)
    USER_ARN=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Arn --output text)
    print_success "Authenticated as: $USER_ARN"
    print_success "Account ID: $ACCOUNT_ID"
else
    print_error "AWS credentials not configured for profile: $AWS_PROFILE"
    exit 1
fi

# Check 4: CloudFormation Stack
print_check "CloudFormation Stack"
STACK_NAME="mark-vle-vector-bucket"
AWS_REGION=${AWS_REGION:-us-west-2}

if aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" &> /dev/null; then
    
    STACK_STATUS=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE" \
        --query 'Stacks[0].StackStatus' \
        --output text)
    
    if [ "$STACK_STATUS" == "CREATE_COMPLETE" ] || [ "$STACK_STATUS" == "UPDATE_COMPLETE" ]; then
        print_success "Stack exists: $STACK_NAME ($STACK_STATUS)"
        
        # Get bucket name from stack
        BUCKET_NAME=$(aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$AWS_REGION" \
            --profile "$AWS_PROFILE" \
            --query 'Stacks[0].Outputs[?OutputKey==`VectorBucketName`].OutputValue' \
            --output text)
        
        print_success "Bucket from stack: $BUCKET_NAME"
    else
        print_warning "Stack status: $STACK_STATUS"
    fi
else
    print_error "CloudFormation stack not found: $STACK_NAME"
    echo "  Run: ./scripts/setup_vector_bucket_and_kb.sh"
    exit 1
fi

# Check 5: S3 Bucket Access
print_check "S3 Bucket Access"
if [ -z "$S3_BUCKET_NAME" ]; then
    S3_BUCKET_NAME=$BUCKET_NAME
fi

if aws s3 ls "s3://$S3_BUCKET_NAME" --profile "$AWS_PROFILE" &> /dev/null; then
    print_success "Can access bucket: $S3_BUCKET_NAME"
    
    # Count embeddings
    EMBEDDING_COUNT=$(aws s3 ls "s3://$S3_BUCKET_NAME/embeddings/blocks/" \
        --profile "$AWS_PROFILE" 2>/dev/null | wc -l | tr -d ' ')
    
    if [ "$EMBEDDING_COUNT" -gt 0 ]; then
        print_success "Found $EMBEDDING_COUNT embeddings"
    else
        print_warning "No embeddings found in bucket"
        echo "  Run: cd scripts && python3 process_block_library.py"
    fi
else
    print_error "Cannot access bucket: $S3_BUCKET_NAME"
    exit 1
fi

# Check 6: Configuration Files
print_check "Configuration Files"

if [ -f "$PROJECT_ROOT/config/config.py" ]; then
    print_success "config.py exists"
    
    # Check if bucket name is in config
    if grep -q "$S3_BUCKET_NAME" "$PROJECT_ROOT/config/config.py"; then
        print_success "Bucket name configured in config.py"
    else
        print_warning "Bucket name not found in config.py"
    fi
else
    print_error "config.py not found"
fi

if [ -f "$PROJECT_ROOT/config/.env" ]; then
    print_success ".env exists"
else
    print_warning ".env not found"
fi

# Check 7: Knowledge Base JSON
print_check "Knowledge Base JSON"
KB_JSON="$PROJECT_ROOT/knowledge-base/markvie_block_library.json"

if [ -f "$KB_JSON" ]; then
    FILE_SIZE=$(stat -f%z "$KB_JSON" 2>/dev/null || stat -c%s "$KB_JSON" 2>/dev/null)
    
    if [ "$FILE_SIZE" -gt 0 ]; then
        print_success "Knowledge base JSON exists ($(numfmt --to=iec-i --suffix=B $FILE_SIZE 2>/dev/null || echo $FILE_SIZE bytes))"
        
        # Validate JSON
        if python3 -c "import json; json.load(open('$KB_JSON'))" 2>/dev/null; then
            BLOCK_COUNT=$(python3 -c "import json; print(len(json.load(open('$KB_JSON'))))")
            print_success "Valid JSON with $BLOCK_COUNT blocks"
        else
            print_error "Invalid JSON format"
        fi
    else
        print_error "Knowledge base JSON is empty"
    fi
else
    print_error "Knowledge base JSON not found: $KB_JSON"
fi

# Check 8: Python Dependencies
print_check "Python Dependencies"
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    print_success "requirements.txt exists"
    
    if [ -d "$PROJECT_ROOT/venv" ]; then
        print_success "Virtual environment exists"
    else
        print_warning "Virtual environment not found"
        echo "  Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    fi
else
    print_error "requirements.txt not found"
fi

# Check 9: Bedrock Access
print_check "Bedrock Access"
if aws bedrock list-foundation-models \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" \
    --query 'modelSummaries[?contains(modelId, `claude`)].modelId' \
    --output text &> /dev/null; then
    print_success "Can access Bedrock models"
else
    print_warning "Cannot access Bedrock (may need to enable in console)"
fi

# Summary
print_header "Verification Summary"

echo ""
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo ""
echo "Configuration:"
echo "  AWS Profile: $AWS_PROFILE"
echo "  AWS Region: $AWS_REGION"
echo "  Account ID: $ACCOUNT_ID"
echo "  S3 Bucket: $S3_BUCKET_NAME"
echo "  Embeddings: $EMBEDDING_COUNT files"
echo ""
echo "Next Steps:"
echo "  1. Test locally:"
echo "     cd $PROJECT_ROOT"
echo "     source venv/bin/activate"
echo "     python3 flask_app.py"
echo ""
echo "  2. Test API:"
echo "     curl -X POST http://localhost:5000/api/chat \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"message\": \"What are the inputs of the TIMER block?\"}'"
echo ""
echo "  3. Deploy to AgentCore (optional):"
echo "     See docs/AGENTCORE_DEPLOYMENT.md"
echo ""
