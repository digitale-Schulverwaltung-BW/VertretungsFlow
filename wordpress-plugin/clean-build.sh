#!/bin/bash
# Clean Build Script for WordPress Plugin

set -e

echo "🧹 Cleaning old build artifacts..."
rm -rf build/
rm -rf node_modules/.vite
rm -rf dist/

echo "📦 Installing dependencies..."
npm install

echo "🔨 Building plugin..."
npm run build

echo "✅ Build complete!"
echo ""
echo "Build file sizes:"
ls -lh build/ | grep -E "index\.(js|css)"
echo ""
echo "Check Tailwind classes in build:"
grep -o "max-w-7xl\|bg-white\|rounded-lg" build/index.js | head -5
echo ""
echo "Check for Bootstrap classes (should be empty):"
grep -o 'className:"[^"]*"' build/index.js | grep -E "col-md|form-control|btn btn" || echo "(None found - good!)"
