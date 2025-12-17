#!/bin/bash

# ArchonAgent Pipeline Prerequisites Verification Script
# This script checks if all prerequisites are met before deploying the pipeline

set -e

echo "=========================================="
echo "ArchonAgent Pipeline Prerequisites Check"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
ALL_CHECKS_PASSED=true

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        ALL_CHECKS_PASSED=false
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check 1: kubectl installed
echo "Checking kubectl installation..."
if command -v kubectl &> /dev/null; then
    KUBECTL_VERSION=$(kubectl version --client --short 2>/dev/null | head -n1)
    print_status 0 "kubectl is installed: $KUBECTL_VERSION"
else
    print_status 1 "kubectl is not installed"
    echo "  Install: https://kubernetes.io/docs/tasks/tools/"
fi
echo ""

# Check 2: AWS CLI installed
echo "Checking AWS CLI installation..."
if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version 2>&1)
    print_status 0 "AWS CLI is installed: $AWS_VERSION"
else
    print_status 1 "AWS CLI is not installed"
    echo "  Install: https://aws.amazon.com/cli/"
fi
echo ""

# Check 3: Node.js and npm installed
echo "Checking Node.js installation..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_status 0 "Node.js is installed: $NODE_VERSION"
    
    # Check version is 18+
    NODE_MAJOR=$(node --version | cut -d'.' -f1 | sed 's/v//')
    if [ "$NODE_MAJOR" -ge 18 ]; then
        print_status 0 "Node.js version is 18 or higher"
    else
        print_status 1 "Node.js version should be 18 or higher (current: $NODE_VERSION)"
    fi
else
    print_status 1 "Node.js is not installed"
    echo "  Install: https://nodejs.org/"
fi

if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    print_status 0 "npm is installed: $NPM_VERSION"
else
    print_status 1 "npm is not installed"
fi
echo ""

# Check 4: CDK CLI installed
echo "Checking AWS CDK installation..."
if command -v cdk &> /dev/null; then
    CDK_VERSION=$(cdk --version 2>&1)
    print_status 0 "AWS CDK is installed: $CDK_VERSION"
else
    print_status 1 "AWS CDK is not installed"
    echo "  Install: npm install -g aws-cdk"
fi
echo ""

# Check 5: AWS credentials configured
echo "Checking AWS credentials..."
if aws sts get-caller-identity &> /dev/null; then
    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=$(aws configure get region || echo "us-east-1")
    print_status 0 "AWS credentials are configured"
    echo "  Account: $AWS_ACCOUNT"
    echo "  Region: $AWS_REGION"
else
    print_status 1 "AWS credentials are not configured"
    echo "  Configure: aws configure"
fi
echo ""

# Check 6: EKS cluster access
echo "Checking EKS cluster access..."
if kubectl cluster-info &> /dev/null; then
    CLUSTER_INFO=$(kubectl cluster-info | head -n1)
    print_status 0 "kubectl can access a Kubernetes cluster"
    echo "  $CLUSTER_INFO"
    
    # Check if it's an EKS cluster
    if kubectl get nodes -o json 2>/dev/null | grep -q "eks.amazonaws.com"; then
        print_status 0 "Cluster appears to be an EKS cluster"
    else
        print_warning "Cluster may not be an EKS cluster"
    fi
else
    print_status 1 "kubectl cannot access a Kubernetes cluster"
    echo "  Configure: aws eks update-kubeconfig --name <cluster-name> --region <region>"
fi
echo ""

# Check 7: Argo Workflows installed
echo "Checking Argo Workflows installation..."
if kubectl get namespace argo &> /dev/null; then
    print_status 0 "argo namespace exists"
    
    if kubectl get deployment -n argo argo-workflows-workflow-controller &> /dev/null || kubectl get deployment -n argo workflow-controller &> /dev/null; then
        print_status 0 "workflow-controller deployment exists"
    else
        print_status 1 "workflow-controller deployment not found"
    fi
    
    if kubectl get deployment -n argo argo-workflows-server &> /dev/null || kubectl get deployment -n argo argo-server &> /dev/null; then
        print_status 0 "argo-server deployment exists"
    else
        print_status 1 "argo-server deployment not found"
    fi
else
    print_status 1 "argo namespace not found"
    echo "  Install: https://argoproj.github.io/argo-workflows/quick-start/"
fi
echo ""

# Check 8: Argo Events installed
echo "Checking Argo Events installation..."
# Check both argo-events namespace and argo namespace (some installations put everything in argo)
if kubectl get namespace argo-events &> /dev/null; then
    print_status 0 "argo-events namespace exists"
    EVENTS_NS="argo-events"
elif kubectl get deployment -n argo argo-events-controller-manager &> /dev/null; then
    print_status 0 "argo-events installed in argo namespace"
    EVENTS_NS="argo"
else
    print_status 1 "argo-events not found"
    echo "  Install: https://argoproj.github.io/argo-events/installation/"
    EVENTS_NS=""
fi

if [ -n "$EVENTS_NS" ]; then
    if kubectl get deployment -n "$EVENTS_NS" argo-events-controller-manager &> /dev/null || kubectl get deployment -n "$EVENTS_NS" eventbus-controller &> /dev/null; then
        print_status 0 "argo-events controller deployment exists"
    else
        print_status 1 "argo-events controller deployment not found"
    fi
fi
echo ""

# Check 9: GitHub token in Secrets Manager
echo "Checking GitHub token in Secrets Manager..."
SECRET_NAME="${GITHUB_TOKEN_SECRET_NAME:-github-token}"
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" &> /dev/null; then
    print_status 0 "GitHub token secret exists: $SECRET_NAME"
else
    print_status 1 "GitHub token secret not found: $SECRET_NAME"
    echo "  Create: aws secretsmanager create-secret --name $SECRET_NAME --secret-string 'your-token'"
fi
echo ""

# Check 10: CDK Bootstrap
echo "Checking CDK bootstrap..."
if aws cloudformation describe-stacks --stack-name CDKToolkit &> /dev/null; then
    BOOTSTRAP_VERSION=$(aws cloudformation describe-stacks --stack-name CDKToolkit --query 'Stacks[0].Outputs[?OutputKey==`BootstrapVersion`].OutputValue' --output text 2>/dev/null || echo "unknown")
    print_status 0 "CDK is bootstrapped (version: $BOOTSTRAP_VERSION)"
else
    print_status 1 "CDK is not bootstrapped"
    echo "  Bootstrap: cdk bootstrap aws://ACCOUNT-ID/REGION"
fi
echo ""

# Check 11: Environment variables
echo "Checking environment variables..."
if [ -n "$GITHUB_OWNER" ]; then
    print_status 0 "GITHUB_OWNER is set: $GITHUB_OWNER"
else
    print_status 1 "GITHUB_OWNER is not set"
    echo "  Set: export GITHUB_OWNER=your-github-username"
fi

if [ -n "$GITHUB_REPO" ]; then
    print_status 0 "GITHUB_REPO is set: $GITHUB_REPO"
else
    print_warning "GITHUB_REPO is not set (will use default: archon-agent)"
fi

if [ -n "$GITHUB_BRANCH" ]; then
    print_status 0 "GITHUB_BRANCH is set: $GITHUB_BRANCH"
else
    print_warning "GITHUB_BRANCH is not set (will use default: main)"
fi
echo ""

# Check 12: aphex-config.yaml exists and is valid
echo "Checking aphex-config.yaml..."
CONFIG_PATH="../aphex-config.yaml"
if [ ! -f "$CONFIG_PATH" ]; then
    CONFIG_PATH="aphex-config.yaml"
fi

if [ -f "$CONFIG_PATH" ]; then
    print_status 0 "aphex-config.yaml exists"
    
    # Check if it contains the placeholder account ID
    if grep -q "123456789012" "$CONFIG_PATH"; then
        print_warning "aphex-config.yaml contains placeholder account ID (123456789012)"
        echo "  Update with your actual AWS account ID"
    else
        print_status 0 "aphex-config.yaml does not contain placeholder account ID"
    fi
else
    print_status 1 "aphex-config.yaml not found"
fi
echo ""

# Summary
echo "=========================================="
if [ "$ALL_CHECKS_PASSED" = true ]; then
    echo -e "${GREEN}All prerequisite checks passed!${NC}"
    echo "You are ready to deploy the pipeline."
    echo ""
    echo "Next steps:"
    echo "  1. cd pipeline"
    echo "  2. npm install"
    echo "  3. npx cdk synth"
    echo "  4. npx cdk deploy"
else
    echo -e "${RED}Some prerequisite checks failed.${NC}"
    echo "Please address the issues above before deploying."
    echo ""
    echo "See pipeline/DEPLOYMENT_GUIDE.md for detailed instructions."
fi
echo "=========================================="
