# chatbot/middle_modules/spacy_nei.py
import spacy

loaded_models = {}

def load_model(model_name):
    if model_name not in loaded_models:
        loaded_models[model_name] = spacy.load(model_name)
    return loaded_models[model_name]
