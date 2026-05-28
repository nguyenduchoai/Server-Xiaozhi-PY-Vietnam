#!/bin/bash

# Script to initialize data volumes directories

set -e

echo "🔧 Initializing data volumes..."

# Define directories to create
DIRS=(
  "data/postgres"
  "data/redis"
  "data/backend/config"
  "data/backend/log"
  "data/backend/assets"
  "data/mcp"
)

# Create each directory if it doesn't exist
for dir in "${DIRS[@]}"; do
  if [ ! -d "$dir" ]; then
    mkdir -p "$dir"
    echo "✅ Created directory: $dir"
  else
    echo "ℹ️  Directory already exists: $dir"
  fi
done

echo "🎉 Volume initialization completed!"
