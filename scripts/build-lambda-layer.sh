#!/bin/bash
# Build Lambda Layer for Archon
# This script creates a Lambda layer with all required Python dependencies

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LAYER_DIR="$PROJECT_ROOT/lambda-layer"
PYTHON_DIR="$LAYER_DIR/python"

echo "Building Lambda layer..."

# Clean previous build
rm -rf "$LAYER_DIR"
mkdir -p "$PYTHON_DIR"

# Install dependencies into the layer directory
# Lambda expects packages in python/ subdirectory
pip install -r "$PROJECT_ROOT/lambda/requirements-layer.txt" \
    --target "$PYTHON_DIR" \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.11 \
    --no-deps

# Install dependencies with their dependencies
pip install -r "$PROJECT_ROOT/lambda/requirements-layer.txt" \
    --target "$PYTHON_DIR" \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --python-version 3.11

# Remove unnecessary files to reduce layer size
find "$PYTHON_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find "$PYTHON_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PYTHON_DIR" -type f -name "*.pyc" -delete
find "$PYTHON_DIR" -type f -name "*.pyo" -delete
find "$PYTHON_DIR" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find "$PYTHON_DIR" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

echo "Lambda layer built successfully at: $LAYER_DIR"
echo "Layer size: $(du -sh "$LAYER_DIR" | cut -f1)"
