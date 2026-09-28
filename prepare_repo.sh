#!/bin/bash
# Script to prepare the repository with explicit task selection

# Function to display usage help
usage() {
    echo "Usage: $0 [--all] [--preprocess] [--cmu] [--vosk] [--piper] [--help]"
    echo "Options:"
    echo "  --all         Run all tasks (preprocess, cmu, vosk, piper)"
    echo "  --preprocess  Run FastText model preprocessing"
    echo "  --cmu         Download CMU dictionary"
    echo "  --vosk        Setup Vosk models"
    echo "  --piper       Setup Piper models"
    echo "  --help        Display this help and exit"
}

# Validate arguments
if [ $# -eq 0 ]; then
    usage
    exit 0
fi

# Initialize flags
run_all=false
run_preprocess=false
run_cmu=false
run_vosk=false
run_piper=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --all)
            run_all=true
            ;;
        --preprocess)
            run_preprocess=true
            ;;
        --cmu)
            run_cmu=true
            ;;
        --vosk)
            run_vosk=true
            ;;
        --piper)
            run_piper=true
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo "Error: Unknown option '$arg'"
            usage
            exit 1
            ;;
    esac
done

# If --all is set, override individual flags
if $run_all; then
    run_preprocess=true
    run_cmu=true
    run_vosk=true
    run_piper=true
fi

# Get script directory
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

# Setup Python environment
setup_env() {
    echo "Setting up Python environment..."
    UV_INSTALLED=false
    PYENV_INSTALLED=false
    PYTHON=python

    if uv --version &>/dev/null; then
        echo "Using uv"
        UV_INSTALLED=true
    fi

    if pyenv --version &>/dev/null; then
        echo "Using pyenv"
        PYENV_INSTALLED=true
    fi

    if python --version &>/dev/null; then
        echo "Python installed"
        PYTHON_INSTALLED=true
    elif python3 --version &>/dev/null; then
        echo "Python3 installed"
        PYTHON_INSTALLED=true
        PYTHON=python3
    else
        echo "Python is not installed!"
        exit 1
    fi

    # Create virtual environment
    echo "Creating virtual environment..."
    if $UV_INSTALLED; then
        echo "Using uv to create venv..."
        uv venv venv -p 3.11
        source venv/bin/activate && uv pip install -r requirements.txt
    elif $PYENV_INSTALLED; then
        echo "Using pyenv to create venv..."
        pyenv init
        pyenv local 3.11
        pyenv exec $PYTHON -m venv venv
        source venv/bin/activate && $PYTHON -m pip install -r requirements.txt
    else
        echo "Using system Python to create venv..."
        $PYTHON -m venv venv
        source venv/bin/activate && $PYTHON -m pip install -r requirements.txt
    fi
}

# Preprocess English FastText model
preprocess() {
    echo "Starting FastText model preprocessing..."
    if [ -f "misc/english_fasttext.kv" ]; then
        echo "FastText model already preprocessed. Skipping."
        return
    fi

    echo "Downloading FastText vectors..."
    wget -O misc/cc.en.300.vec.gz https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.en.300.vec.gz
    gunzip misc/cc.en.300.vec.gz

    echo "Converting to gensim format..."
    source venv/bin/activate
    python -c "
from gensim.models import KeyedVectors
m = KeyedVectors.load_word2vec_format('misc/cc.en.300.vec', binary=False, limit=500000)
m.save('misc/english_fasttext.kv')
print('Done')
"

    echo "Cleaning up..."
    rm misc/cc.en.300.vec
    echo "Preprocessing completed."
}

# Download CMU dictionary
cmu_download() {
    echo "Downloading CMU dictionary..."
    source venv/bin/activate
    python -c "import nltk; nltk.download('cmudict')"
    echo "CMU dictionary downloaded."
}

# Setup Vosk models
vosk_setup() {
    echo "Setting up Vosk models..."
    mkdir -p "$SCRIPT_DIR/models/vosk/"

    # Small French model
    if [ ! -f "models/vosk/vosk-model-small-fr-0.22.zip" ]; then
        curl -o models/vosk/vosk-model-small-fr-0.22.zip https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip
    fi
    tar -xvf models/vosk/vosk-model-small-fr-0.22.zip -C models/vosk/ || unzip models/vosk/vosk-model-small-fr-0.22.zip -d models/vosk/
    rm models/vosk/fr_sm
    ln -s "$SCRIPT_DIR/models/vosk/vosk-model-small-fr-0.22/" models/vosk/fr_sm

    # Small English model
    if [ ! -f "models/vosk/vosk-model-small-en-us-0.15.zip" ]; then
        curl -o models/vosk/vosk-model-small-en-us-0.15.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    fi
    unzip models/vosk/vosk-model-small-en-us-0.15.zip -d models/vosk/
    rm models/vosk/en_sm
    ln -s "$SCRIPT_DIR/models/vosk/vosk-model-small-en-us-0.15/" models/vosk/en_sm

    # Full French model
    if [ ! -f "models/vosk/vosk-model-fr-0.22.zip" ]; then
        curl -o models/vosk/vosk-model-fr-0.22.zip https://alphacephei.com/vosk/models/vosk-model-fr-0.22.zip
    fi
    tar -xvf models/vosk/vosk-model-fr-0.22.zip -C models/vosk/ || unzip models/vosk/vosk-model-fr-0.22.zip -d models/vosk/
    rm models/vosk/fr
    ln -s "$SCRIPT_DIR/models/vosk/vosk-model-fr-0.22/" models/vosk/fr

    # Full English model
    if [ ! -f "models/vosk/vosk-model-en-us-0.22.zip" ]; then
        curl -o models/vosk/vosk-model-en-us-0.22.zip https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip
    fi
    unzip models/vosk/vosk-model-en-us-0.22.zip -d models/vosk/
    rm models/vosk/en
    ln -s "$SCRIPT_DIR/models/vosk/vosk-model-en-us-0.22/" models/vosk/en

    echo "Vosk models setup completed."
}

# Setup Piper models
piper_setup() {
    echo "Setting up Piper models..."
    mkdir -p "$SCRIPT_DIR/models/piper/"
    
    echo "Downloading Piper voice models..."
    cd "$SCRIPT_DIR/models/piper/" && python3 -m piper.download_voices en_US-lessac-medium
    echo "Piper models downloaded."
}

# Main execution
echo "Starting repository preparation..."

# Always run environment setup
setup_env

# Run selected tasks
if $run_preprocess; then preprocess; fi
if $run_cmu; then cmu_download; fi
if $run_vosk; then vosk_setup; fi
if $run_piper; then piper_setup; fi

echo "Repository preparation completed."

