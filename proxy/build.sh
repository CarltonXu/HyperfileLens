#!/bin/bash

# HyperFileLens Proxy Build Script

set -e

echo "Building HyperFileLens Proxy..."

# Build for multiple platforms
echo "Building for Linux amd64..."
GOOS=linux GOARCH=amd64 go build -o bin/proxy-linux-amd64 .

echo "Building for Linux arm64..."
GOOS=linux GOARCH=arm64 go build -o bin/proxy-linux-arm64 .

echo "Building for Windows amd64..."
GOOS=windows GOARCH=amd64 go build -o bin/proxy-windows-amd64.exe .

echo "Building for macOS amd64..."
GOOS=darwin GOARCH=amd64 go build -o bin/proxy-darwin-amd64 .

echo "Building for macOS arm64..."
GOOS=darwin GOARCH=arm64 go build -o bin/proxy-darwin-arm64 .

echo "Build complete! Binaries available in bin/"
ls -la bin/
