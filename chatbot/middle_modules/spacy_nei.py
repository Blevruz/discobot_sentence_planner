# chatbot/middle_modules/spacy_nei.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
import utils.config

import spacy

class SpacyNEI(DummyMiddle):

    def __init__(self, name="spacy_nei", **args):
        DummyMiddle.__init__(self, name, **args)
        self._loop_type = 'process'
        self.model = args.get('model', "en_core_web_sm")
        self.nlp = spacy.load(self.model)

    def action(self, i):
        if not self.input_queue.empty():
            text = self.input_queue.get()
            entities = self.extract_entities(text)
            self.output_queue.put(entities)

    def extract_entities(self, text):
        doc = self.nlp(text)
        entities = []

        for ent in doc.ents:
            entities.append((ent.text, ent.label_))
        return entities

middle_modules_class['spacy_nei'] = SpacyNEI
