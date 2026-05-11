# chatbot/middle_modules/dark_lapsus.py

import re
import random
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.darkcerveau import DarkBrain
import utils.config


def _corriger_elision(texte):
    """Corrects French elision errors.
    Expands incorrect apostrophes (e.g. "d'manger" -> "de manger")
    and contracts missing ones (e.g. "de ami" -> "d'ami").
    """
    def expand(match):
        prefix = match.group(1).lower()
        next_word = match.group(2)
        if prefix == 'qu': return f"que {next_word}"
        if prefix == 'c':  return f"ce {next_word}"
        return f"{prefix}e {next_word}"

    texte = re.sub(
        r"\b([dljmnts]|qu|c)'([b-df-gj-np-tv-xz]\w+)",
        expand, texte, flags=re.IGNORECASE
    )

    def contract(match):
        prefix = match.group(1)
        vowel_word = match.group(2)
        if prefix.lower() == "que": return f"qu'{vowel_word}"
        return f"{prefix[0]}'{vowel_word}"

    texte = re.sub(
        r"\b(le|la|de|ne|me|te|se|que)\s+([aeiouyàâéèêëîïôùûü]\w+)",
        contract, texte, flags=re.IGNORECASE
    )

    return texte


def _get_excuse_graduelle(compteur, mot_correct):
    """Returns an increasingly dramatic apology interjection."""
    mot_maj = mot_correct.upper()
    if compteur == 1:
        return random.choice([f"... Oups ! {mot_maj} !", f"... Pardon, {mot_maj} !"])
    elif compteur == 2:
        return random.choice([f"... Encore ?! {mot_maj} !", f"... Mes circuits chauffent ! {mot_maj} !"])
    else:
        return random.choice([f"... MAIS C'EST PAS VRAI ! {mot_maj} !!!", f"... BUG CRITIQUE ! {mot_maj} !!!"])


class DarkLapsus(DummyMiddle):
    """Applies randomised dark-semantic lapsus to incoming French text.

    Receives a plain French string, randomly replaces content words
    with phonetically similar but semantically dark alternatives
    (using DarkBrain / Silero), corrects French elision around the
    substitution, and appends a self-correcting excuse interjection.

    Meant to sit between a transcriber (e.g. FasterWhisper) and an
    LLM module or a TTS output. The optional LLM conclusion step
    should be handled by a downstream LLMRequest module.

    Parameters
    ----------
    lexique_path : str
        Path to the Lexique383 TSV file. Default '../Lexique383.tsv'.
    vectors_path : str
        Path to the FastText .kv file. Default '../fasttext_navel_lite.kv'.
    niveau_dark : float
        Darkness weight (0.0–1.0). Higher pulls replacements toward
        semantically darker words. Default 0.5.
    niveau_rime : float
        Phonetic similarity weight (0.0–1.0). Higher enforces closer
        phonetic matches. Default 0.5.
    proba_lapsus : float
        Probability that any given sentence undergoes a lapsus
        substitution (0.0–1.0). Default 0.5.
    mode_random : bool
        If True, pick randomly among the top-3 candidates instead of
        always the best-scoring one. Default True.
    idle_sleep_s : float
        Seconds to sleep when the input queue is empty. Default 0.005.
    """

    def action(self, i):
        import time

        text = self.input_queue.get()

        if text is None:
            time.sleep(self.idle_sleep_s)
            return

        phrases = re.split(r'(?<=[.!?])\s+', text)
        construit = []
        cpt_lapsus = 0

        for p in phrases:
            if not p.strip():
                continue

            # Skip this sentence by chance
            if random.random() > self.proba_lapsus:
                construit.append(p)
                continue

            # Find the last interesting content word in the sentence
            mots = re.findall(r'\b\w+\b', p)
            mot_cle = None
            for m in reversed(mots):
                if len(m) > 2 and self._brain.est_mot_interessant(m):
                    mot_cle = m
                    break

            if mot_cle:
                lapsus = self._brain.trouver_lapsus(
                    mot_cle,
                    self.niveau_dark,
                    self.niveau_rime,
                    self.mode_random
                )
                if lapsus:
                    cpt_lapsus += 1
                    # Replace last occurrence (reverse trick for rightmost match)
                    p_mod = p[::-1].replace(mot_cle[::-1], lapsus[::-1], 1)[::-1]
                    p_corrected = _corriger_elision(p_mod)
                    excuse = _get_excuse_graduelle(cpt_lapsus, mot_cle)
                    construit.append(f"{p_corrected} {excuse}")
                    utils.config.debug_print(
                        f"[{self.name}] Lapsus: {mot_cle} -> {lapsus} "
                        f"(corrected: '{p_corrected}')"
                    )
                else:
                    construit.append(p)
            else:
                construit.append(p)

        if cpt_lapsus > 0:
            result = " ".join(construit)
            utils.config.debug_print(
                f"[{self.name}] {cpt_lapsus} lapsus applied. Output: {result}"
            )
            self.output_queue.put(result)
        else:
            # No lapsus: pass the original text through unchanged
            utils.config.debug_print(f"[{self.name}] No lapsus triggered.")
            self.output_queue.put(text)

    def __init__(self, name="dark_lapsus", **args):
        super().__init__(name, **args)
        self._loop_type = "thread"
        self.datatype_in = "string"
        self.datatype_out = "string"

        self.niveau_dark   = args.get('niveau_dark',   0.5)
        self.niveau_rime   = args.get('niveau_rime',   0.5)
        self.proba_lapsus  = args.get('proba_lapsus',  0.5)
        self.mode_random   = args.get('mode_random',   True)
        self.idle_sleep_s  = args.get('idle_sleep_s',  0.005)

        lexique_path = args.get('lexique_path', 'misc/Lexique383.tsv')
        vectors_path = args.get('vectors_path', 'misc/fasttext_navel_lite.kv')

        utils.config.debug_print(
            f"[{self.name}] Loading DarkBrain "
            f"(lexique={lexique_path}, vectors={vectors_path})..."
        )
        self._brain = DarkBrain(
            path_lexique=lexique_path,
            path_vectors=vectors_path
        )

        utils.config.debug_print(
            f"[{self.name}] DarkLapsus ready — "
            f"dark={self.niveau_dark}, rime={self.niveau_rime}, "
            f"proba={self.proba_lapsus}, random={self.mode_random}"
        )


middle_modules_class['dark_lapsus'] = DarkLapsus
