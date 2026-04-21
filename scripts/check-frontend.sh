#!/usr/bin/env bash
# Run all frontend code quality checks.
# Usage: ./scripts/check-frontend.sh [--fix]

set -euo pipefail

FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"

cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
    echo "Installing frontend dev dependencies..."
    npm install
fi

if [ "${1:-}" = "--fix" ]; then
    echo "==> Formatting frontend files with Prettier..."
    npm run format

    echo "==> Auto-fixing ESLint issues..."
    npm run lint:fix

    echo "Frontend formatting and lint fixes applied."
else
    echo "==> Checking formatting with Prettier..."
    npm run format:check

    echo "==> Linting JavaScript with ESLint..."
    npm run lint

    echo "All frontend quality checks passed."
fi
