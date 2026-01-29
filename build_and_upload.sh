#!/bin/bash

# Exit on error
set -e

# NB: Make sure you bump the version in pyproject.toml and src/yo_claude/__init__.py first

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf dist/
rm -rf build/
rm -rf *.egg-info/
rm -rf src/*.egg-info/

# Build the package
echo "📦 Building package..."
python -m build

# Upload to PyPI
echo "🚀 Uploading to PyPI..."
python -m twine upload dist/*

echo "✅ Done!"
