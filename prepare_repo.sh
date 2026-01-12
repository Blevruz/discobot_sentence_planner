#!/bin/bash
# Gestion de la version de Python sur environnement Linux
# et installation des dépendances
UV_INSTALLED=false
PYENV_INSTALLED=false
if uv --version > /dev/null; then
    echo "uv is installed"
    UV_INSTALLED=true
fi
if pyenv --version > /dev/null; then
    echo "pyenv is installed"
    PYENV_INSTALLED=true
fi

if $UV_INSTALLED; then
# En utilisant uv:
    uv python install 3.11
    uv venv venv
    source venv/bin/activate && uv pip install -r requirements.txt
# En utilisant pyenv:
elif $PYENV_INSTALLED; then
    pyenv init && pyenv local 3.11.2
    pyenv exec python3 -m venv venv || python3 -m venv venv
    source venv/bin/activate && python -m pip install -r requirements.txt
fi


# Gestion des modèles de STT Vosk
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
mkdir -p $SCRIPT_DIR/models/vosk/
curl -o models/vosk/vosk-model-small-fr-0.22.zip https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip
tar -xvf models/vosk/vosk-model-small-fr-0.22.zip -C models/vosk/ || unzip models/vosk/vosk-model-small-fr-0.22.zip -d models/vosk/
rm models/vosk/fr
ln -s $SCRIPT_DIR/models/vosk/vosk-model-small-fr-0.22/ models/vosk/fr
curl -o models/vosk/vosk-model-small-en-us-0.15.zip https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip || tar -xvf models/vosk/vosk-model-small-en-us-0.15.zip -C models/vosk/
unzip models/vosk/vosk-model-small-en-us-0.15.zip -d models/vosk/
rm models/vosk/en
ln -s $SCRIPT_DIR/models/vosk/vosk-model-small-en-us-0.15/ models/vosk/en
