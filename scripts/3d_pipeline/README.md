# 3D Model Generation Pipeline

Generate interactive 3D models from robot product photos using Hunyuan3D 2.1.

## Prerequisites

- Python 3.10+
- NVIDIA GPU with 12GB+ VRAM (3080Ti or better)
- CUDA 12.x toolkit

## Setup

```bash
cd scripts/3d_pipeline

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Hunyuan3D-2
git clone https://github.com/Tencent/Hunyuan3D-2 /tmp/hunyuan3d
cd /tmp/hunyuan3d && pip install -e .
cd -

# Configure environment
cp ../../.env.example .env
# Edit .env with your SUPABASE_URL and SUPABASE_SECRET_KEY
```

## Usage

### Full Pipeline

```bash
./run_pipeline.sh
```

### Individual Steps

```bash
# 1. Assess current image quality
python assess_images.py

# 2. Enhance images (background removal + upscaling)
python enhance_images.py

# 3. Generate 3D models
python generate_3d.py --robot "CC1 Pro"          # single robot
python generate_3d.py --all                       # all robots
python generate_3d.py --all --skip-existing       # skip already generated

# 4. Upload to Supabase
python upload_models.py --robot "CC1 Pro"
python upload_models.py --all
```

### Generation Options

```bash
python generate_3d.py --robot "CC1 Pro" \
  --steps 50 \
  --seed 42 \
  --max-triangles 100000 \
  --max-file-size-mb 5 \
  --retry 3
```

## Output Structure

```
output/
├── image_assessment.json       # Image quality report
├── enhanced/                   # Background-removed images
│   └── cc1_pro/
│       └── enhanced_1.png
└── models/                     # Generated 3D models
    ├── generation_report.json
    └── cc1_pro/
        ├── model_raw.glb       # Raw generation output
        ├── model.glb           # Optimized GLB (web)
        ├── model.usdz          # iOS AR format
        └── poster.webp         # Static preview image
```

## Notes

- First run downloads ~8GB of model weights to `~/.cache/huggingface/`
- Generation takes 2-5 minutes per robot on a 3080Ti
- GLB files are optimized to < 5MB for web delivery
- USDZ conversion requires `usd-core` (Pixar's USD Python library)
