# chatbot/utils/englishcerveau.py
"""
English version of DarkBrain (darkcerveau.py).

Instead of finding phonetically similar but semantically DARK words (French version),
this finds phonetically similar but semantically FAR words — i.e. words that sound
similar but mean something completely different.

Requires a gensim KeyedVectors (.kv) file for English word embeddings.
The path defaults to 'misc/english_fasttext.kv' but must exist at startup —
the module will exit with an error if the file is not found or cannot be loaded.

Requirements:
    pip install nltk gensim Levenshtein
    python -c "import nltk; nltk.download('cmudict')"
"""

import os
import sys
import random
from nltk.corpus import cmudict
from Levenshtein import distance as lev_dist
import utils.config


# Common stop words to skip
STOP_WORDS = {
    'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'she', 'it', 'they',
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'need', 'dare', 'ought',
    'and', 'but', 'or', 'nor', 'for', 'yet', 'so', 'of', 'in', 'on',
    'at', 'to', 'by', 'up', 'as', 'if', 'this', 'that', 'these', 'those',
    'not', 'no', 'yes', 'very', 'just', 'also', 'than', 'then', 'so',
}


def _phonemes_to_str(phoneme_list):
    """Convert a list of CMU phonemes to a string for Levenshtein comparison.
    Strips stress markers (digits) from vowels.
    e.g. ['T', 'EY1', 'B', 'AH0', 'L'] -> 'TEYBAL'  (approx)
    We keep digits for better discrimination but could strip them.
    """
    return ''.join(phoneme_list)


class EnglishBrain:
    """
    Finds phonetically similar but semantically distant word substitutions
    for English lapsus generation.

    Parameters
    ----------
    vectors_path : str
        Path to a gensim KeyedVectors file (.kv) for English word embeddings.
        Defaults to 'misc/english_fasttext.kv'. The file must exist — the module
        will exit with an error if it is missing or cannot be loaded.
    """

    def __init__(self, vectors_path='misc/english_fasttext.kv'):
        print("[ENGLISHBRAIN] Loading CMU Pronouncing Dictionary...")
        self._cmu = cmudict.dict()

        # Build a flat word->phoneme_str lookup for fast access
        # Keep only the first pronunciation variant
        self._phoneme_map = {}
        for word, prons in self._cmu.items():
            if prons:
                self._phoneme_map[word] = _phonemes_to_str(prons[0])

        if not os.path.exists(vectors_path):
            print(f"[ERREUR] {vectors_path} introuvable.")
            sys.exit(1)

        print(f"[ENGLISHBRAIN] Loading word vectors from {vectors_path}...")
        try:
            import gensim.models
            self._model = gensim.models.KeyedVectors.load(vectors_path, mmap='r')
            print("[ENGLISHBRAIN] Vectors loaded.")
        except Exception as e:
            print(f"[ERREUR] Could not load vectors from {vectors_path}: {e}")
            sys.exit(1)

        print(f"[ENGLISHBRAIN] Ready. Dictionary has {len(self._phoneme_map)} words.")

    def est_mot_interessant(self, word):
        """Return True if word is a content word worth replacing."""
        word = word.lower()
        if word in STOP_WORDS:
            return False
        if len(word) < 3:
            return False
        return word in self._phoneme_map

    def trouver_lapsus(self, word, niveau_phonetique=0.5, mode_random=False):
        """
        Find a phonetically similar but semantically distant replacement.

        Parameters
        ----------
        word : str
            The source word to replace.
        niveau_phonetique : float
            How strict phonetic similarity must be (0=loose, 1=strict).
            Higher values require closer phonetic matches.
        mode_random : bool
            If True, pick randomly from top-3 candidates.

        Returns
        -------
        str or None
            Replacement word, or None if no candidate found.
        """
        word = word.lower()

        if word not in self._phoneme_map:
            return None

        target_phon = self._phoneme_map[word]
        target_len = len(target_phon)

        # Find phonetically similar candidates
        max_dist = int(6 - (niveau_phonetique * 4))  # 2 to 6 depending on strictness
        candidates = []

        for candidate, phon_str in self._phoneme_map.items():
            if candidate == word:
                continue
            if len(candidate) < 3:
                continue
            if candidate in STOP_WORDS:
                continue
            # Quick length filter before expensive Levenshtein
            if abs(len(phon_str) - target_len) > max_dist + 2:
                continue

            dist = lev_dist(target_phon, phon_str)
            if dist <= max_dist and dist > 0:
                candidates.append((candidate, dist))

        if not candidates:
            return None

        # Sort by phonetic closeness
        candidates.sort(key=lambda x: x[1])
        # Take top 50 most phonetically similar
        candidates = candidates[:50]

        # Score by semantic distance (we want MAXIMUM distance)
        scored = []
        for candidate, phon_dist in candidates:
            if candidate in self._model and word in self._model:
                try:
                    sim = self._model.similarity(word, candidate)
                    # We want semantically FAR words, so low similarity = good
                    semantic_score = 1.0 - max(0.0, sim)
                except Exception:
                    semantic_score = 0.5
            else:
                semantic_score = 0.5  # unknown words get neutral score

            phonetic_score = 1.0 / (1.0 + phon_dist)
            # Balance: phonetic closeness + semantic distance
            final = phonetic_score * 0.4 + semantic_score * 0.6
            scored.append((candidate, final))

        scored.sort(key=lambda x: x[1], reverse=True)

        if not scored:
            return None

        top_3 = scored[:3]
        utils.config.debug_print(
            f"[ENGLISHBRAIN] Top candidates for '{word}': "
            f"{[(w, round(s, 2)) for w, s in top_3]}"
        )

        if mode_random and len(top_3) > 1:
            return random.choice(top_3)[0]
        return top_3[0][0]
