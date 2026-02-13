# chatbot/middle_modules/spacy_features.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
import utils.config
import utils.spacy

import spacy

raise NotImplementedError, "Not implemented yet"

class SpacyFeatures(DummyMiddle):
    """Feature extraction using spaCy.
    """

    def __init__(self, name="spacy_nei", **args):
        super().__init__(name, **args)
        self._loop_type = 'process'
        self.datatype_in = 'string'
        self.model = args.get('model', "en_core_web_sm")
        self.nlp = utils.spacy.load_model(self.model)

    def action(self, i):
        text = self.input_queue.get()
        if text:
            entities = self.extract_entities(text)
            self.output_queue.put(entities)

    def extract_entities(self, text):
        doc = self.nlp(text)
        entities = []

        for ent in doc.ents:
            entities.append((ent.text, ent.label_))
        return entities

middle_modules_class['spacy_nei'] = SpacyNEI
