# chatbot/cerveau.py
import pandas as pd
import numpy as np
import gensim.models
from Levenshtein import distance as lev_dist
import sys
import os
import random
import utils.config


class DarkBrain:
    def __init__(self, path_lexique='Lexique383.tsv',
                 path_vectors='../fasttext_navel_lite.kv'):
        """
        Parameters
        ----------
        path_lexique : str
            Path to the Lexique383 TSV file.
        path_vectors : str
            Path to the FastText KeyedVectors (.kv) file.
        """
        print("[CERVEAU] Initialisation des modules linguistiques...")

        # 1. LEXICON
        if not os.path.exists(path_lexique):
            alt = os.path.join('Lexique383', path_lexique)
            if os.path.exists(alt):
                path_lexique = alt
            else:
                print(f"[ERREUR] {path_lexique} introuvable.")
                sys.exit(1)

        print(f" -> Chargement de Lexique3 ({path_lexique})...")
        self.lexique = pd.read_csv(path_lexique, sep='\t')
        self.lexique = self.lexique[['ortho', 'phon', 'cgram']]
        self.lexique = self.lexique[self.lexique['cgram'].isin(['NOM', 'ADJ', 'VER'])]
        self.lexique['ortho'] = self.lexique['ortho'].astype(str)
        self.lexique = self.lexique.drop_duplicates(subset=['ortho'])

        # 2. EMBEDDINGS
        if not os.path.exists(path_vectors):
            print(f"[ERREUR] {path_vectors} introuvable.")
            sys.exit(1)

        print(f" -> Chargement de FastText ({path_vectors})...")
        try:
            self.model = gensim.models.KeyedVectors.load(path_vectors, mmap='r')
        except Exception:
            print("[INFO] Chargement format texte (lent)...")
            self.model = gensim.models.KeyedVectors.load_word2vec_format(
                path_vectors, binary=False, limit=500_000
            )

        # 3. DARK CONCEPT VECTOR
        dark_seeds = [
            "mort", "mourant", "triste", "erreur", "fatal", "néant", "souffrance",
            "bug", "panne", "virus", "destruction", "fin", "tombe", "froid",
            "sang", "peur", "mauvais", "haine", "danger", "pourri", "vide",
            "pathétique", "misérable", "atroce", "sale", "faux", "menace", "stupide", "idiot",
            "folie", "dément", "psychose", "hystérie", "rage", "délire", "absurde",
            "meurtre", "tueur", "assassin", "torture", "violence", "arme", "poison",
            "enfer", "diable", "démon", "maudit", "sinistre", "macabre", "horreur", "terreur",
            "criminel", "détenu", "prison", "coupable", "vile", "mortel"
        ]
        self.dark_vector = self._create_concept_vector(dark_seeds)
        print("[CERVEAU] Module prêt.")

    # ------------------------------------------------------------------
    def _create_concept_vector(self, words):
        vectors = [self.model[w] for w in words if w in self.model]
        if not vectors:
            return np.zeros(300)
        return np.mean(vectors, axis=0)

    # ------------------------------------------------------------------
    def est_mot_interessant(self, mot):
        """Return True if *mot* is a content word (NOM/ADJ/VER) and not
        a grammatical stop-word."""
        mot = mot.lower()

        STOP_WORDS = {
            "lui", "elle", "nous", "vous", "ils", "elles",
            "les", "des", "aux", "mes", "tes", "ses", "nos", "vos", "leurs",
            "est", "sont", "ont", "font", "vont", "vas", "fais", "suis", "es", "ai", "as", "a",
            "avec", "sans", "pour", "dans", "sur", "sous", "par",
            "cette", "cet", "ce", "ces", "mon", "ton", "son",
            "mais", "ou", "et", "donc", "or", "ni", "car",
            "je", "tu", "il", "on", "ça", "ceci", "cela",
            "pas", "plus", "moins", "très", "trop",
        }

        if mot in STOP_WORDS:
            return False

        return not self.lexique[self.lexique['ortho'] == mot].empty

    # ------------------------------------------------------------------
    def trouver_lapsus(self, mot_cible, niveau_dark=0.8,
                       niveau_rime=0.5, mode_random=False):
        """Find a phonetically similar but semantically dark replacement
        for *mot_cible*.

        Parameters
        ----------
        mot_cible : str
            The source word to replace.
        niveau_dark : float
            Weight toward dark semantics (0.0–1.0).
        niveau_rime : float
            Strictness of phonetic similarity (0.0–1.0).
        mode_random : bool
            Pick randomly from top-3 candidates instead of the best one.

        Returns
        -------
        str or None
            The replacement word, or None if no suitable candidate found.
        """
        mot_cible = mot_cible.lower()

        row = self.lexique[self.lexique['ortho'] == mot_cible]
        if row.empty:
            return None
        target_phon = str(row.iloc[0]['phon'])
        target_pos  = row.iloc[0]['cgram']

        len_p = len(target_phon)
        candidates = self.lexique[
            (self.lexique['cgram'] == target_pos) &
            (self.lexique['phon'].str.len().between(len_p - 2, len_p + 2)) &
            (self.lexique['ortho'] != mot_cible)
        ].copy()

        if candidates.empty:
            return None

        candidates['dist'] = candidates['phon'].apply(
            lambda x: lev_dist(target_phon, str(x))
        )

        suffixe_cible = mot_cible[-3:] if len(mot_cible) > 3 else ""

        def check_keep(row):
            max_dist = int(6 - (niveau_rime * 4))
            if row['dist'] <= max_dist:
                return True
            if (suffixe_cible and len(row['ortho']) > 3
                    and row['ortho'].endswith(suffixe_cible)):
                return True
            return False

        candidates = candidates[candidates.apply(check_keep, axis=1)].copy()
        if candidates.empty:
            return None

        candidates['score_phon'] = 1 / (1 + candidates['dist'])

        scored_candidates = []
        for _, row in candidates.iterrows():
            word = str(row['ortho'])

            utils.config.debug_print(f"[LAPSUS] {word} of type {type(word)} ({row['cgram']})")
            if word.startswith(mot_cible) or mot_cible.startswith(word):
                continue

            sem_score = 0.0
            if word in self.model:
                try:
                    raw_sim = self.model.cosine_similarities(
                        self.dark_vector, [self.model[word]]
                    )[0]
                    sem_score = max(0.0, raw_sim)
                except Exception:
                    sem_score = 0.0

            if sem_score < 0.1 * niveau_dark:
                continue

            weight_phon  = 2.0 * (1.1 - niveau_dark)
            weight_sem   = 5.0 * niveau_dark
            power_factor = 1.0 + (niveau_dark * 2.0)
            sem_boosted  = sem_score ** power_factor

            suffix_bonus = 0.0
            if len(mot_cible) > 2 and len(word) > 2:
                if mot_cible[-2:] == word[-2:]:
                    suffix_bonus = 0.3
                if (len(mot_cible) > 3 and len(word) > 3
                        and mot_cible[-3:] == word[-3:]):
                    suffix_bonus = 0.6

            final_score = (
                row['score_phon'] * weight_phon
                + sem_boosted * weight_sem
                + suffix_bonus
            )
            scored_candidates.append((word, final_score, sem_score))

        if not scored_candidates:
            return None

        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        top_3 = scored_candidates[:3]
        print(f"   [DEBUG] Top 3 pour '{mot_cible}': "
              f"{[(w, round(s, 2)) for w, s, _ in top_3]}")

        if mode_random and len(top_3) > 1:
            return random.choice(top_3)[0]
        return top_3[0][0]
