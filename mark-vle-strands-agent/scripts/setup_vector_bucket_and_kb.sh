#!/bin/bash

##############################################################################
# Mark Vle Agent - Vector Bucket and Knowledge Base Setup
# 
# This script:
# 1. Creates an S3 Vector Bucket using CloudFormation
# 2. Processes the block library JSON and generates embeddings
# 3. Uploads embeddings to the vector bucket
##############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CF_TEMPLATE="$PROJECT_ROOT/cloudformation/vector-bucket.yaml"

# Load deployment configuration from .deploy.env if it exists
DEPLOY_ENV_FILE="$PROJECT_ROOT/.deploy.env"
if [ -f "$DEPLOY_ENV_FILE" ]; then
    print_message "$BLUE" "Loading configuration from .deploy.env"
    # Source the file to load variables
    set -a  # Automatically export all variables
    source "$DEPLOY_ENV_FILE"
    set +a
fi

# Read from environment variables or use defaults
STACK_NAME="${STACK_NAME:-mark-vle-vector-bucket}"
DEFAULT_BUCKET_NAME="${BUCKET_NAME:-markvie-vectors}"
DEFAULT_REGION="${REGION:-us-west-2}"
DEFAULT_ENVIRONMENT="${ENVIRONMENT:-production}"

# Function to print colored messages
print_message() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

print_header() {
    echo ""
    print_message "$BLUE" "=========================================="
    print_message "$BLUE" "$1"
    print_message "$BLUE" "=========================================="
}

print_success() {
    print_message "$GREEN" "✓ $1"
}

print_error() {
    print_message "$RED" "✗ $1"
}

print_warning() {
    print_message "$YELLOW" "⚠ $1"
}

# Function to check if AWS CLI is installed
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    print_success "AWS CLI found"
}

# Function to check if Python is installed
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install it first."
        exit 1
    fi
    print_success "Python 3 found"
}

# Function to get user input with default value
get_input() {
    local prompt=$1
    local default=$2
    local var_name=$3
    
    read -p "$(echo -e ${YELLOW}${prompt} [${default}]: ${NC})" input
    eval $var_name="${input:-$default}"
}

# Function to check if CloudFormation stack exists
stack_exists() {
    if [ -z "$AWS_PROFILE" ]; then
        aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$REGION" \
            &> /dev/null
    else
        aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$REGION" \
            --profile "$AWS_PROFILE" \
            &> /dev/null
    fi
    return $?
}

# Function to wait for stack operation to complete
wait_for_stack() {
    local operation=$1
    print_message "$YELLOW" "Waiting for stack $operation to complete..."
    
    aws cloudformation wait "stack-${operation}-complete" \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --profile "$AWS_PROFILE"
    
    if [ $? -eq 0 ]; then
        print_success "Stack $operation completed successfully"
        return 0
    else
        print_error "Stack $operation failed"
        return 1
    fi
}

# Function to create or update CloudFormation stack
deploy_stack() {
    print_header "Step 1: Deploying S3 Vector Bucket"
    
    if stack_exists; then
        print_warning "Stack already exists. Updating..."
        
        aws cloudformation update-stack \
            --stack-name "$STACK_NAME" \
            --template-body "file://$CF_TEMPLATE" \
            --parameters \
                ParameterKey=VectorBucketName,ParameterValue="$BUCKET_NAME" \
                ParameterKey=Environment,ParameterValue="$ENVIRONMENT" \
            --region "$REGION" \
            --profile "$AWS_PROFILE" \
            --capabilities CAPABILITY_IAM
        
        if [ $? -eq 0 ]; then
            wait_for_stack "update"
        else
            # Check if no updates are needed
            if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --profile "$AWS_PROFILE" &> /dev/null; then
                print_warning "No updates needed for the stack"
            else
                print_error "Failed to update stack"
                exit 1
            fi
        fi
    else
        print_message "$YELLOW" "Creating new stack..."
        
        aws cloudformation create-stack \
            --stack-name "$STACK_NAME" \
            --template-body "file://$CF_TEMPLATE" \
            --parameters \
                ParameterKey=VectorBucketName,ParameterValue="$BUCKET_NAME" \
                ParameterKey=Environment,ParameterValue="$ENVIRONMENT" \
            --region "$REGION" \
            --profile "$AWS_PROFILE" \
            --capabilities CAPABILITY_IAM
        
        if [ $? -eq 0 ]; then
            wait_for_stack "create"
        else
            print_error "Failed to create stack"
            exit 1
        fi
    fi
}

# Function to get stack outputs
get_stack_outputs() {
    print_header "Retrieving Stack Outputs"
    
    FULL_BUCKET_NAME=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --profile "$AWS_PROFILE" \
        --query 'Stacks[0].Outputs[?OutputKey==`VectorBucketName`].OutputValue' \
        --output text)
    
    BUCKET_ARN=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --profile "$AWS_PROFILE" \
        --query 'Stacks[0].Outputs[?OutputKey==`VectorBucketArn`].OutputValue' \
        --output text)
    
    print_success "Bucket Name: $FULL_BUCKET_NAME"
    print_success "Bucket ARN: $BUCKET_ARN"
}

# Function to update config file with bucket name
update_config() {
    print_header "Step 2: Updating Configuration"
    
    CONFIG_FILE="$PROJECT_ROOT/config/config.py"
    ENV_FILE="$PROJECT_ROOT/config/.env"
    
    # Update config.py default value
    if [ -f "$CONFIG_FILE" ]; then
        # Update the default S3_BUCKET_NAME in config.py
        if grep -q "S3_BUCKET_NAME.*os.getenv" "$CONFIG_FILE"; then
            # Update the default value in the os.getenv call
            sed -i.bak "s/S3_BUCKET_NAME.*os.getenv('S3_BUCKET_NAME', '[^']*')/S3_BUCKET_NAME: str = os.getenv('S3_BUCKET_NAME', '$FULL_BUCKET_NAME')/" "$CONFIG_FILE"
            print_success "Updated S3_BUCKET_NAME default in config.py"
        else
            print_warning "S3_BUCKET_NAME pattern not found in config.py"
        fi
    else
        print_warning "Config file not found: $CONFIG_FILE"
    fi
    
    # Create or update .env file
    print_message "$YELLOW" "Creating/updating .env file..."
    
    if [ -f "$ENV_FILE" ]; then
        # Update existing .env file
        if grep -q "^S3_BUCKET_NAME=" "$ENV_FILE"; then
            sed -i.bak "s|^S3_BUCKET_NAME=.*|S3_BUCKET_NAME=$FULL_BUCKET_NAME|" "$ENV_FILE"
            print_success "Updated S3_BUCKET_NAME in .env"
        else
            echo "S3_BUCKET_NAME=$FULL_BUCKET_NAME" >> "$ENV_FILE"
            print_success "Added S3_BUCKET_NAME to .env"
        fi
        
        if grep -q "^AWS_REGION=" "$ENV_FILE"; then
            sed -i.bak "s|^AWS_REGION=.*|AWS_REGION=$REGION|" "$ENV_FILE"
        else
            echo "AWS_REGION=$REGION" >> "$ENV_FILE"
        fi
    else
        # Create new .env file
        cat > "$ENV_FILE" << EOF
# Mark Vle Agent Configuration
# Generated by setup_vector_bucket_and_kb.sh on $(date)

# AWS Configuration
AWS_REGION=$REGION
S3_BUCKET_NAME=$FULL_BUCKET_NAME

# Embedding Model
EMBEDDING_MODEL=amazon.titan-embed-text-v2:0

# Agent Configuration
AGENT_TEMPERATURE=0.7
AGENT_MAX_TOKENS=2000

# RAG Configuration
RAG_MAX_RESULTS=3
RAG_SIMILARITY_THRESHOLD=0.5

# LiteLLM Proxy (Optional)
# LITELLM_PROXY_URL=http://localhost:4000
# LITELLM_API_KEY=your-api-key
# LITELLM_MODEL=litellm_proxy/bedrock-claude-sonnet-4.5

# AgentCore Identity (Optional)
# AGENT_IDENTITY_NAME=your-identity-name
# AGENT_IDENTITY_SCOPES=read,write
EOF
        print_success "Created .env file"
    fi
    
    print_success "Configuration updated successfully"
    echo ""
    print_message "$BLUE" "Configuration files:"
    echo "  - config.py: $CONFIG_FILE"
    echo "  - .env: $ENV_FILE"
}

# Function to process knowledge base
process_knowledge_base() {
    print_header "Step 3: Processing Knowledge Base"
    
    KB_SCRIPT="$SCRIPT_DIR/process_block_library.py"
    
    if [ ! -f "$KB_SCRIPT" ]; then
        print_error "Knowledge base script not found: $KB_SCRIPT"
        exit 1
    fi
    
    # Check if virtual environment exists
    if [ -d "$PROJECT_ROOT/venv" ]; then
        print_message "$YELLOW" "Activating virtual environment..."
        source "$PROJECT_ROOT/venv/bin/activate"
    else
        print_warning "Virtual environment not found. Using system Python."
    fi
    
    # Set environment variables for the script
    export AWS_PROFILE="$AWS_PROFILE"
    export AWS_REGION="$REGION"
    export S3_BUCKET_NAME="$FULL_BUCKET_NAME"
    
    print_message "$YELLOW" "Running knowledge base processing script..."
    python3 "$KB_SCRIPT"
    
    if [ $? -eq 0 ]; then
        print_success "Knowledge base processed successfully"
    else
        print_error "Failed to process knowledge base"
        exit 1
    fi
}

# Function to display summary
display_summary() {
    print_header "Deployment Summary"
    
    echo ""
    print_message "$GREEN" "✓ S3 Vector Bucket Created"
    echo "  Bucket Name: $FULL_BUCKET_NAME"
    echo "  Bucket ARN: $BUCKET_ARN"
    echo "  Region: $REGION"
    echo ""
    print_message "$GREEN" "✓ Configuration Updated"
    echo "  config.py: Updated default S3_BUCKET_NAME"
    echo "  .env: Created/updated with bucket name and region"
    echo ""
    print_message "$GREEN" "✓ Knowledge Base Processed"
    echo "  Embeddings uploaded to: s3://$FULL_BUCKET_NAME/embeddings/"
    echo ""
    print_message "$BLUE" "Configuration Files:"
    echo "  - $PROJECT_ROOT/config/config.py"
    echo "  - $PROJECT_ROOT/config/.env"
    echo ""
    print_message "$BLUE" "Next Steps:"
    echo "  1. Review configuration in config/.env"
    echo "  2. Update IAM roles to grant access to the vector bucket"
    echo "  3. Test the agent locally:"
    echo "     cd $PROJECT_ROOT"
    echo "     source venv/bin/activate"
    echo "     python3 flask_app.py"
    echo "  4. Deploy to AgentCore if needed (see docs/AGENTCORE_DEPLOYMENT.md)"
    echo ""
    print_message "$YELLOW" "To delete the stack:"
    echo "  # Empty bucket first"
    echo "  aws s3 rm s3://$FULL_BUCKET_NAME --recursive --region $REGION --profile $AWS_PROFILE"
    echo "  # Delete stack"
    echo "  aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION --profile $AWS_PROFILE"
    echo ""
}

##############################################################################
# Main Script
##############################################################################

print_header "Mark Vle Agent - Vector Bucket & Knowledge Base Setup"

# Check prerequisites
check_aws_cli
check_python

# Get user inputs
echo ""
print_message "$BLUE" "Please provide the following information:"
echo ""

# Check if running in non-interactive mode (CI/CD)
if [ -n "$CI" ] || [ "$NON_INTERACTIVE" = "true" ]; then
    print_message "$YELLOW" "Running in non-interactive mode"
    # Use environment variables or defaults
    AWS_PROFILE="${AWS_PROFILE:-}"
    REGION="${REGION:-$DEFAULT_REGION}"
    BUCKET_NAME="${BUCKET_NAME:-$DEFAULT_BUCKET_NAME}"
    ENVIRONMENT="${ENVIRONMENT:-$DEFAULT_ENVIRONMENT}"
    
    print_message "$GREEN" "Using configuration from environment variables"
else
    get_input "AWS Profile" "${AWS_PROFILE:-default}" AWS_PROFILE
    get_input "AWS Region" "$DEFAULT_REGION" REGION
    get_input "Vector Bucket Name (without account ID)" "$DEFAULT_BUCKET_NAME" BUCKET_NAME
    get_input "Environment" "$DEFAULT_ENVIRONMENT" ENVIRONMENT
fi

# Confirm settings
echo ""
print_header "Configuration Summary"
echo "AWS Profile: ${AWS_PROFILE:-<using GitHub Actions credentials>}"
echo "AWS Region: $REGION"
echo "Bucket Name: $BUCKET_NAME-<account-id>"
echo "Environment: $ENVIRONMENT"
echo "CloudFormation Stack: $STACK_NAME"
echo ""

# Skip confirmation in non-interactive mode
if [ -n "$CI" ] || [ "$NON_INTERACTIVE" = "true" ]; then
    print_message "$YELLOW" "Auto-proceeding in non-interactive mode"
else
    read -p "$(echo -e ${YELLOW}Proceed with deployment? [y/N]: ${NC})" confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        print_warning "Deployment cancelled"
        exit 0
    fi
fi

# Execute deployment steps
deploy_stack
get_stack_outputs
update_config
process_knowledge_base
display_summary

print_success "Setup completed successfully!"
