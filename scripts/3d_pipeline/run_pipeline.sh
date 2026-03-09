#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================="
echo "3D Model Generation Pipeline"
echo "=================================="

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "Virtual environment activated."
fi

# Step 1: Assess images
echo ""
echo "Step 1: Assessing images..."
python assess_images.py

# Step 2: Enhance images (background removal)
echo ""
echo "Step 2: Enhancing images..."
python enhance_images.py

# Step 3: Generate 3D models
echo ""
echo "Step 3: Generating 3D models..."
python generate_3d.py --all --skip-existing

# Step 4: Upload to Supabase
echo ""
echo "Step 4: Uploading models..."
python upload_models.py --all

echo ""
echo "=================================="
echo "Pipeline complete!"
echo "=================================="
