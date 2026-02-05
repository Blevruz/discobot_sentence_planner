#!/bin/bash
# Gestion de la version de Python sur environnement Linux
# et installation des dépendances
UV_INSTALLED=false
PYENV_INSTALLED=false
PYTHON=python
if uv --version > /dev/null; then
    echo "uv is installed"
    UV_INSTALLED=true
fi
if pyenv --version > /dev/null; then
    echo "pyenv is installed"
    PYENV_INSTALLED=true
fi
if python --version > /dev/null; then
    echo "python is installed"
    PYTHON_INSTALLED=true
elif
    python3 --version > /dev/null; then
    echo "python3 is installed"
    PYTHON_INSTALLED=true
    PYTHON=python3
else
    echo "python is not installed!"
    exit 1
fi

if $UV_INSTALLED; then
# En utilisant uv:
    uv $PYTHON install 3.11
    uv venv venv
    source venv/bin/activate && uv pip install -r requirements.txt
# En utilisant pyenv:
else
    if $PYENV_INSTALLED; then
    	pyenv init && pyenv local 3.11.2
    	pyenv exec $PYTHON -m venv venv 
    else
	$PYTHON -m venv venv
    fi
    source venv/bin/activate && $PYTHON -m pip install -r requirements.txt
fi


# Gestion des modèles de STT Vosk
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
mkdir -p $SCRIPT_DIR/models/vosk/
if [ ! -f models/vosk/vosk-model-small-fr-0.22.zip ]; then
    curl -o models/vosk/vosk-model-small-fr-0.22.zip https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip
tar -xvf models/vosk/vosk-model-small-fr-0.22.zip -C models/vosk/ || unzip models/vosk/vosk-model-small-fr-0.22.zip -d models/vosk/
rm models/vosk/fr_sm
ln -s $SCRIPT_DIR/models/vosk/vosk-model-small-fr-0.22/ models/vosk/fr_sm
if [ ! -f models/vosk/vosk-model-small-en-us-0.15.zip ]; then
    curl -o models/vosk/vosk-model-small-en-us-0.15.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip || tar -xvf models/vosk/vosk-model-small-en-us-0.15.zip -C models/vosk/
unzip models/vosk/vosk-model-small-en-us-0.15.zip -d models/vosk/
rm models/vosk/en_sm
ln -s $SCRIPT_DIR/models/vosk/vosk-model-small-en-us-0.15/ models/vosk/en_sm

if [ ! -f models/vosk/vosk-model-fr-0.22.zip ]; then
    curl -o models/vosk/vosk-model-fr-0.22.zip https://alphacephei.com/vosk/models/vosk-model-fr-0.22.zip
tar -xvf models/vosk/vosk-model-fr-0.22.zip -C models/vosk/ || unzip models/vosk/vosk-model-fr-0.22.zip -d models/vosk/
rm models/vosk/fr
ln -s $SCRIPT_DIR/models/vosk/vosk-model-fr-0.22/ models/vosk/fr
if [ ! -f models/vosk/vosk-model-en-us-0.22.zip ]; then
    curl -o models/vosk/vosk-model-en-us-0.22.zip https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip || tar -xvf models/vosk/vosk-model-en-us-0.22.zip -C models/vosk/
unzip models/vosk/vosk-model-en-us-0.22.zip -d models/vosk/
rm models/vosk/en
ln -s $SCRIPT_DIR/models/vosk/vosk-model-en-us-0.22/ models/vosk/en

# Gestion des modèles de TTS Piper
#
mkdir -p $SCRIPT_DIR/models/piper/
#curl -o models/piper/piper-models.zip https://github.com/rhasspy/piper/releases/download/v0.1.0/piper-models.zip
cd $SCRIPT_DIR/models/piper/ && python3 -m piper.download_voices en_US-lessac-medium
