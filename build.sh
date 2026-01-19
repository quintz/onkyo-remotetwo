#!/bin/bash

set -e

VERSION="0.1.0"
PACKAGE_NAME="ucr2-intg-onkyo-${VERSION}"

echo "Building Onkyo Integration v${VERSION}..."

# Clean previous builds
rm -rf build/ dist/ *.tar.gz

# Build with PyInstaller using Docker
echo "Building binary with PyInstaller..."
docker run --rm --name onkyo-builder \
    --platform=linux/arm64 \
    --user=$(id -u):$(id -g) \
    -v "$PWD":/workspace \
    docker.io/unfoldedcircle/r2-pyinstaller:3.11.13 \
    bash -c \
      "PYTHON_VERSION=\$(python --version | cut -d' ' -f2 | cut -d. -f1,2) && \
      python -m pip install --user -r requirements.txt && \
      PYTHONPATH=~/.local/lib/python\${PYTHON_VERSION}/site-packages:\$PYTHONPATH pyinstaller --clean --onedir --name driver -y \
        intg-onkyo/driver.py"

# Create package structure
echo "Creating package..."
mkdir -p ${PACKAGE_NAME}/bin
mkdir -p ${PACKAGE_NAME}/config

# Copy binary
cp -r dist/driver/* ${PACKAGE_NAME}/bin/

# Copy metadata
cp driver.json ${PACKAGE_NAME}/

# Create tarball
echo "Creating tarball..."
tar -czf ${PACKAGE_NAME}.tar.gz ${PACKAGE_NAME}

# Cleanup
rm -rf ${PACKAGE_NAME}

echo ""
echo "✅ Build complete!"
echo ""
echo "Package: ${PACKAGE_NAME}.tar.gz"
echo ""
echo "To install on Remote Two:"
echo "1. Go to http://your-remote-ip"
echo "2. Settings → Integrations → Install"
echo "3. Upload ${PACKAGE_NAME}.tar.gz"
echo ""
