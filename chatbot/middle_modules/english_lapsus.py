# chatbot/middle_modules/english_lapsus.py
"""
English version of the DarkLapsus module (dark_lapsus.py).

Takes an English sentence, probabilistically replaces a content word with a
phonetically similar but semantically distant alternative (a "lapsus"), then
appends a self-correcting interjection.

Julien's suggestion:
  "Take a word in the sentence, get its embedding, find another word that's
   phonologically close but semantically far, and replace the word."

Pipeline position: sits between a transcriber (e.g. FasterWhisper) and the LLM.

Parameters
----------
vectors_path : str
    Path to English FastText/Word2Vec .kv file. Default 'misc/english_fasttext.kv'.
    The file must exist — the module will exit with an error if it is missing.
niveau_phonetique : float
    Phonetic similarity strictness (0.0-1.0). Higher = closer sound match.
    Default 0.5.
proba_lapsus : float
    Probability a given sentence gets a lapsus (0.0-1.0). Default 0.4.
mode_random : bool
    If True, pick randomly from top-3 candidates. Default True.
idle_sleep_s : float
    Sleep time when queue is empty. Default 0.005.
"""

import re
import random
import time
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.englishcerveau import EnglishBrain
import utils.config


def _get_interjection(counter, correct_word):
    """Return an increasingly dramatic self-correction interjection."""
    word_upper = correct_word.upper()
    if counter == 1:
        return random.choice([
            f"... Oops! {word_upper}!",
            f"... Sorry, I meant {word_upper}!",
        ])
    elif counter == 2:
        return random.choice([
            f"... Again?! {word_upper}!",
            f"... My circuits are glitching! {word_upper}!",
        ])
    else:
        return random.choice([
            f"... CRITICAL BUG! {word_upper}!!!",
            f"... SYSTEM ERROR! I MEANT {word_upper}!!!",
        ])


class EnglishLapsus(DummyMiddle):
    """
    Applies randomised phonetic lapsus to incoming English text.

    Receives a plain English string, randomly replaces a content word
    with a phonetically similar but semantically distant alternative,
    then appends a self-correcting interjection.

    Sits between a transcriber and an LLM or TTS module.
    """

    def action(self, i):
        text = self.input_queue.get()

        if text is None:
            time.sleep(self.idle_sleep_s)
            return

        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        result_parts = []
        lapsus_count = 0

        for sentence in sentences:
            if not sentence.strip():
                continue

            # Skip by chance
            if random.random() > self.proba_lapsus:
                result_parts.append(sentence)
                continue

            # Find the last interesting content word
            words = re.findall(r'\b[a-zA-Z]+\b', sentence)
            target_word = None
            for w in reversed(words):
                if self._brain.est_mot_interessant(w.lower()):
                    target_word = w
                    break

            if target_word:
                replacement = self._brain.trouver_lapsus(
                    target_word.lower(),
                    self.niveau_phonetique,
                    self.mode_random
                )

                if replacement:
                    lapsus_count += 1
                    # Replace last occurrence of target word (case-insensitive)
                    pattern = re.compile(re.escape(target_word), re.IGNORECASE)
                    # Replace only the last occurrence
                    matches = list(pattern.finditer(sentence))
                    if matches:
                        last = matches[-1]
                        modified = (sentence[:last.start()]
                                    + replacement
                                    + sentence[last.end():])
                        interjection = _get_interjection(lapsus_count, target_word)
                        result_parts.append(f"{modified} {interjection}")
                        utils.config.debug_print(
                            f"[{self.name}] Lapsus: '{target_word}' -> '{replacement}'"
                        )
                    else:
                        result_parts.append(sentence)
                else:
                    result_parts.append(sentence)
            else:
                result_parts.append(sentence)

        output = ' '.join(result_parts)

        if lapsus_count > 0:
            utils.config.debug_print(
                f"[{self.name}] {lapsus_count} lapsus applied. Output: {output}"
            )

        self.output_queue.put(output)

    def __init__(self, name="english_lapsus", **args):
        super().__init__(name, **args)
        self._loop_type = "thread"
        self.datatype_in = "string"
        self.datatype_out = "string"

        self.niveau_phonetique = args.get('niveau_phonetique', 0.5)
        self.proba_lapsus = args.get('proba_lapsus', 0.4)
        self.mode_random = args.get('mode_random', True)
        self.idle_sleep_s = args.get('idle_sleep_s', 0.005)

        vectors_path = args.get('vectors_path', 'misc/english_fasttext.kv')

        utils.config.debug_print(f"[{self.name}] Loading EnglishBrain...")
        self._brain = EnglishBrain(vectors_path=vectors_path)
        utils.config.debug_print(
            f"[{self.name}] EnglishLapsus ready — "
            f"phonetique={self.niveau_phonetique}, "
            f"proba={self.proba_lapsus}, random={self.mode_random}"
        )


middle_modules_class['english_lapsus'] = EnglishLapsus
