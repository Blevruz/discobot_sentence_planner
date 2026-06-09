#!/bin/bash
set -e

# Activate the virtual environment
source venv/bin/activate

# Set cache directory
export HF_HOME=/root/.cache/faster_whisper

# Download models
echo "Downloading faster-whisper models..."
python - <<EOF
from faster_whisper import WhisperModel

models = ['small', 'medium', 'large']  # Add any other models you need

for model in models:
    print(f'Downloading model: {model}')
    WhisperModel(model, device='cpu', compute_type='int8')
EOF

echo "Models downloaded and cached successfully!"
