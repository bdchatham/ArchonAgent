# Archon Build Scripts

This directory contains build and deployment scripts for Archon.

## Scripts

### build-lambda-layer.sh

Builds the Lambda layer with Python dependencies for Archon Lambda functions.

**Usage:**
```bash
./scripts/build-lambda-layer.sh
```

**What it does:**
1. Creates `lambda-layer/python/` directory
2. Installs dependencies from `lambda/requirements-layer.txt`
3. Optimizes layer size by removing unnecessary files
4. Outputs layer size and location

**Requirements:**
- Python 3.11
- pip
- Internet connection (to download packages)

**Output:**
- `lambda-layer/` directory ready for CDK deployment

**Notes:**
- Run this before deploying CDK stacks
- Re-run when dependencies change
- Layer is excluded from git (see .gitignore)

## Adding New Scripts

When adding new scripts:
1. Make them executable: `chmod +x scripts/your-script.sh`
2. Add shebang: `#!/bin/bash`
3. Use `set -e` for error handling
4. Document in this README
