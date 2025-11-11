#!/bin/bash

echo "Running Python linting and formatting checks..."

# Run black check
echo "Checking Python formatting with black..."
black --check . --exclude "venv|node_modules|dist"

# Run flake8
echo "Running flake8..."
flake8 . --exclude=venv,node_modules,dist

echo "Running TypeScript linting..."
npm run lint

echo "Checking TypeScript formatting..."
npm run format:check

echo "All checks complete!"
