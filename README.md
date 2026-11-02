# DISCOBOT

**Designing an LLM-powered user-centered knowledge graph for social robots to
mitigate loneliness among university students.**

DISCOBOT is the Lab-STICC social-robotics project. It is a small framework for
building conversational-robot pipelines out of interchangeable modules (speech
recognition, LLM, text-to-speech, web interfaces, ...) wired together by a JSON
file. The current target hardware is a NAO robot (the Navel robot from navel
robotics GmbH is also supported), and the repository includes the setup used
for a user experiment in which a robot comments on participants while they
complete poem and number-series tasks.

Contents:

1. [Quick start](#quick-start)
2. [Installation](#installation)
3. [Running](#running)
4. [Architecture](#architecture)
5. [Configuration files](#configuration-files)
6. [The experiment pipeline](#the-experiment-pipeline)
7. [Module reference](#module-reference)
8. [Writing a new module](#writing-a-new-module)
9. [Repository layout](#repository-layout)
10. [Tests](#tests)
11. [Known issues](#known-issues)

## Quick start

```bash
./prepare_repo.sh --deps           # create ./venv and install requirements
./run.sh --config configs/dummy_config.json --verbose    # smoke test, no hardware
./run.sh --config configs/discobot_experiment/nao_config_en.json --test-config
```

The last command only validates the config (see [Running](#running)); it does
not need the robot, but the `$VARIABLES` in the config must be set.

## Installation

Linux only for now. A Windows setup would be a welcome contribution.

Requirements: Python 3.11, `portaudio` headers (for PyAudio), and, for
GPU transcription, a CUDA-capable machine. `requirements.txt` pins everything,
including `torch`, the `nvidia-*` CUDA wheels, spaCy's `en_core_web_sm`, and
`qi` (the NAOqi SDK bindings used to talk to NAO).

`prepare_repo.sh` takes explicit flags and **does nothing but print its usage
when run without arguments**:

| Flag           | What it does                                                          |
|----------------|-----------------------------------------------------------------------|
| `--deps`       | Create `./venv` (with `uv`, `pyenv` or system Python 3.11) and install `requirements.txt`. The environment is in fact always set up, whichever flags you pass. |
| `--cmu`        | Download the NLTK CMU pronouncing dictionary.                          |
| `--vosk`       | Download the Vosk models (small and full, French and English) into `models/vosk/`. Large download. |
| `--piper`      | Download the Piper `en_US-lessac-medium` voice into `models/piper/`.   |
| `--preprocess` | Download the English FastText vectors and convert them to `misc/english_fasttext.kv` (used by `english_lapsus`). Large download. |
| `--all`        | `--preprocess --cmu --vosk --piper`.                                   |

`download_models.sh` pre-downloads the faster-whisper `small`, `medium` and
`large` models; the `Dockerfile` calls it at build time.

### Docker

```bash
docker build -t discobot .
docker run --rm -it --env-file .env discobot --config configs/discobot_experiment/nao_config_en.json
```

The image is based on `nvidia/cuda:12.8.0`, installs the requirements with
`uv`, caches the faster-whisper models, and uses `run.sh` as its entry point,
so arguments go straight to `chatbot/main.py`. Pass `--gpus all` and publish
`$HTTP_PORT` as needed.

## Running

`run.sh` changes into the repository root (config paths such as
`@misc/html/poems.html` are relative to it) and runs `chatbot/main.py` with
the virtualenv's Python:

```bash
./run.sh --config <file.json> [--verbose] [--log <file>] [--test-config]
./run.sh --input <module> [--middle <module> ...] --output <module>
```

| Option                | Meaning                                                                 |
|-----------------------|-------------------------------------------------------------------------|
| `--config FILE`       | Build the pipeline from a JSON config (the normal way).                 |
| `--test-config`       | Validate the config (structure, module names, link targets) and exit. Add `--verbose` to see the unrolled config and the "Config test successful!" message. |
| `--input/--middle/--output` | Quick linear pipeline from module names, e.g. `--input keyboard --middle repeater --output console`. Module names are the file names in `chatbot/*_modules/`, without `.py`. Default for input and output is `dummy`. |
| `--verbose`           | Print debug information, indented by call depth.                       |
| `--log FILE`          | Append the debug information to a file.                                 |

After starting every module, `main.py` idles until Ctrl-C, then stops each
module (threads and processes are given about a second to exit before being
terminated).

### Environment variables

Any config value of the form `"$NAME"` is read from the environment when the
config is loaded; a missing variable is an error and an empty one is a warning.
The experiment configs use:

| Variable            | Used for                                                                  |
|---------------------|---------------------------------------------------------------------------|
| `NAO_IP`            | Address of the NAO robot (audio input, text to speech).                   |
| `LLM_URL`           | Base URL of an OpenAI-compatible server (the module appends `/v1/chat/completions`), e.g. `http://localhost:8000`. |
| `HTTP_PORT`         | Port of the experiment web server (pages, operator and WoZ endpoints).   |
| `QUESTIONNAIRE_URL` | Link to the questionnaire shown on the intro page.                       |

## Architecture

A pipeline is a directed graph of **modules** joined by **queues**.

```
 input module  ──queue──▶  middle module(s)  ──queue──▶  output module
 (data enters)             (transform, route)            (data leaves)
```

- **Input modules** (`chatbot/input_modules/`) bring data in from outside:
  keyboard, stdin, microphones, WAV files, the NAO's audio stream, HTTP POSTs.
- **Middle modules** (`chatbot/middle_modules/`) transform, filter, route or
  combine data: voice activity detection, speech recognition, the LLM service,
  TTS, regexp substitution, toggles, and so on.
- **Output modules** (`chatbot/output_modules/`) send data out: console,
  stdout, audio playback, NAO LEDs, HTTP pages.

Every module derives from `DummyModule` (`chatbot/utils/dummy_module.py`),
which provides:

- **Slots.** A slot is a named group of queues, with a datatype (`string`,
  `dict`, `audio`, `signal`, `any`, ...). Every module has a `default` slot
  on each side, and may define more (the LLM modules have `text`, `cmd`,
  `trigger`, `events`, ...). An *output* slot copies each item to **every**
  queue linked to it (fan-out). An *input* slot reads from whichever linked
  queue has data (fan-in, round-robin).
- **A loop.** `_loop_type` is `'thread'`, `'process'` (separate
  `multiprocessing.Process`, for CPU-heavy work) or `'blocking'`. The loop
  calls `action(i)` repeatedly until the module is stopped. `module_start()`
  and `module_stop()` are hooks.
- **Queues** are `multiprocessing.Queue` wrappers (`chatbot/utils/queues.py`),
  so modules may be threads or processes interchangeably.

Link datatypes are checked when linking; `any` matches everything.

## Configuration files

A config is a JSON list of module entries:

```json
{
    "name": "nao_tts",
    "module": "middle_modules.nao_tts",
    "args": { "ip": "$NAO_IP", "language": "English" },
    "links": [
        { "name": "nao_tts_to_stt_toggle",
          "from_slot": "default",
          "target_name": "stt",
          "to_slot": "toggle_stt" }
    ]
}
```

| Field    | Meaning                                                                    |
|----------|----------------------------------------------------------------------------|
| `name`   | Unique instance name; other modules refer to it in `target_name`.          |
| `module` | `<input\|middle\|output>_modules.<file name without .py>`.                 |
| `args`   | Keyword arguments for the module's constructor (optional).                 |
| `links`  | Outgoing links (optional): this module's `from_slot` → `target_name`'s `to_slot`. `name` labels the queue in debug output. |

Links always point *forward*: a module declares where its output goes.

### Argument syntax

Strings in `args` (recursively, inside dicts and lists) are processed when
the config is loaded:

| Prefix        | Meaning                                                           |
|---------------|-------------------------------------------------------------------|
| `$NAME`       | Value of the environment variable `NAME`.                         |
| `@path.json`  | Contents of that JSON file, parsed.                               |
| `@path.txt`   | Contents of that file as a string (any extension but `.json`).    |

Paths are relative to the repository root. The result is processed again, so
an env variable may itself hold an `@file` reference.

### Meta-modules

Large pipelines are split into reusable sub-configs, which are expanded
("unrolled") into the main graph before loading.

- `"module": "meta.module"` with `"config": "path/to/sub.json"` inserts the
  modules of that file. Their names are prefixed with the meta-module's name
  (`llm` + `llm_service` → `llm_llm_service`).
- Inside the sub-config, a module of type `meta.io` (conventionally named
  `io`) marks the sub-graph's **ports**. Its `links` say where each port
  leads inside the sub-graph.
- From outside, you link to the meta-module by its name, using the port name
  as `to_slot`. Links *from* the sub-graph to the outside are declared in the
  parent's entry for the meta-module, using the port name as `from_slot`.

Example, from `stt.json` and `nao_config_en.json`. In `stt.json`, `io` has a
link `from_slot: "audio_input"` → `toggle_block`, so the parent's
`nao_audio_input → stt` link with `to_slot: "audio_input"` is rewired to land
on `stt_toggle_block`. The recognized text leaves through the `text` port,
which the parent's `stt` entry routes to `llm`'s `text` port.

Meta-modules nest. Links to ports that lead nowhere inside the sub-graph are
dropped (with a debug message).

## The experiment pipeline

`configs/discobot_experiment/` holds the setup for the DISCOBOT user study.
A participant works through poem and number-series tasks on a web page while
the NAO, driven by an LLM, comments, with a human operator able to step in
("Wizard of Oz").

### Main file: `nao_config_en.json`

```
 NAO microphone ─▶ [stt] ─▶ text ─────────────┐
 keyboard ─────────────────────────────────────▶ [llm] ─▶ generated_text ─▶ nao_tts ─▶ NAO speaker
 web pages / operator ─▶ [http] ─▶ operator_command ─▶    │                  └▶ console
                                                           └─ (nao_tts toggles stt so the robot does not hear itself)
```

| Block   | Config                | What it contains |
|---------|-----------------------|------------------|
| `stt`   | `utils/stt.json`      | Toggle (mute while the robot speaks) → WebRTC VAD → faster-whisper → length filter (5 to 500 characters). Also emits `speech_toggle` events when speech starts and ends. |
| `llm`   | `utils/llm.json`      | The conversation engine, described below. |
| `http`  | `utils/http.json`     | Operator and participant HTTP inputs plus the pages, described below. |
| `nao_tts` | built in            | NAO text to speech; sends a toggle to `stt` so that recognition pauses while the robot talks. |

`navel_test_config.json` and `nao_test_config.json` are smaller variants for
testing the Navel and NAO robots respectively.

### The LLM block (`utils/llm.json`)

A conversation is a message list held by `llm_service` (initialised from
`misc/expe_context.json`, which holds an example dialogue between
`<[EXAMPLE START]>` and `<[EXAMPLE END]>` markers). Other modules edit and
query it through a small command protocol (`chatbot/utils/llm_service/`):

| `op`       | Effect |
|------------|--------|
| `APPEND`   | Add messages at the end. |
| `INSERT`   | Insert messages after the message with `anchor_id` (or at the start). |
| `DELETE`   | Remove messages by `ids`. |
| `REPLACE`  | Replace the range `start_id`..`end_id`. |
| `QUERY`    | Return the current messages and context `version`. |
| `GENERATE` | Stream a completion from the model (`/v1/chat/completions`, `stream: true`), emitting `token` events and then `generation_done`. |

Each command is `{"id", "from", "op", "payload"}`; the service answers with
`response` messages (status plus result) and `event` messages. Every message
in the store gets a `msg_id`.

The flow around it:

1. `user_string_to_llm_append` turns text into an `APPEND` of a `user` message.
   When the service confirms, its `trigger` output fires
   (`mute_toggle_block` → `llm_generate_on_trigger`), which sends `GENERATE`.
   Likewise `system_string_to_llm_append` and `assistant_string_to_llm_append`
   append `system` and `assistant` messages without triggering.
2. `llm_output_router` sorts the service's output: `event` messages go to
   `llm_generate_on_trigger` (which forwards tokens), `response` messages go
   back to the appenders' `control` slot.
3. Tokens go to `token_accumulator`, which groups them into sentences so that
   the TTS can start speaking before the whole answer is generated. Sentences
   leave through the `generated_text` port. The complete answer is also
   buffered and appended to the context as an `assistant` message.
4. `deaf_toggle_block` and `mute_toggle_block` implement the operator's
   **deaf** (new context is discarded) and **mute** (generation is not
   triggered) switches. Each `toggle_block` flips state on any signal sent to
   its `block` slot.
5. `context_query` exposes the live context over HTTP (see below).

`llm_service` args: `url` (`$LLM_URL`), `api` (default `/v1/chat/completions`),
`headers`, `temperature`, `max_tokens`, `context` (initial messages).

### The HTTP block

`http_core.json` / `http.json` define the inputs, and
`http_order_E.json` / `http_order_O.json` define the participant-facing pages.
All are served on `$HTTP_PORT` by one shared server
(`chatbot/utils/http_server.py`).

Participant flow, in the *E* ordering: `/intro` → `/poems_familiarization` →
`/robot_familiarization` → `/poems_main` → `/series_familiarization` →
`/series_main`. The *O* ordering runs the series tasks first (the robot
familiarization appears once, between the first familiarization and the first
main task). Pages are templates in `misc/html/`, filled with the `variables`
of the `output_modules.http` entry (`poems-*.json`, `series-*.json`, `nextStage`,
`robotActive`, `commentAfterBlanks`, ...). In the `*-0` files and in the
familiarization stages the robot is inactive.

Endpoints:

| Route                   | Method | Purpose |
|-------------------------|--------|---------|
| `/woz`                  | GET    | Operator ("Wizard of Oz") interface. |
| `/operator_command`     | POST   | Operator text, appended to the LLM context as a `system` message. |
| `/woz_input`            | POST   | JSON messages from the WoZ page (see below). |
| `/user_website_input`   | POST   | Events from the participant pages (answers, inactivity). |
| `/context_query`        | POST   | `APPEND`/`REPLACE`/`DELETE`/`QUERY` on the LLM context; also accepts `{"type": "system_prompt" \| "assistant_speech", "content": ...}`. |
| `/context_result`       | GET    | The latest live context (waits briefly for a snapshot at least as new as the last write). |
| `/sse`                  | GET    | Server-sent events telling the WoZ page the context changed. |

Messages handled by `woz_handler` (the `woz_router`): `{"type": "system_prompt",
"content"}` → append as `system`; `{"type": "assistant_speech", "content"}` →
append as `assistant` *and* speak it; `toggle_deaf`; `toggle_mute`;
`{"userMessage": ...}` → append as `user` and trigger generation; and
`{"inactivityTrigger": true, "message": ...}` → treated like a user message.
Plain strings pass through as `system` messages.

### Experimental conditions: `config_{A,B}{E,O}.json`

The four files are the same pipeline as `nao_config_en.json`, differing in two
choices:

| Letter | Choice | Difference |
|--------|--------|------------|
| **A** / **B** | LLM block | **A** uses `utils/llm_lapsus.json`: temperature 0.6, and the generated text passes through `english_lapsus`, which with probability 0.05 per sentence swaps a content word for a phonetically similar, semantically distant one and adds a self-correction ("... Oops! WORD!"). **B** uses the plain `utils/llm.json` (temperature 0.1). |
| **E** / **O** | Page order | **E** uses `utils/http_order_E.json` (poems first, then series); **O** uses `utils/http_order_O.json` (series first, then poems). |

So `config_AE.json` is the lapsus condition with poems first, and
`config_BO.json` the plain condition with series first.

Before a session, fill in `misc/explanation_en.txt` (currently a placeholder
with instructions for the experimenter): it is shown on the intro page.

## Module reference

Module names are the file names in `chatbot/<type>_modules/`. Each file's
docstring documents its slots and arguments.

**Input**: `keyboard`, `stdin`, `http` (POST endpoint), `nao_audio` (NAO
microphone stream via `qi`), `pyaudio`, `sounddevice`, `wav`, `helloworld`
and `triplet_generator` (test sources), `dummy`.

**Output**: `console`, `stdout`, `http` (serves a templated HTML page),
`pyaudio` (audio playback), `nao_led`, `dummy`.

**Middle**

| Group | Modules |
|-------|---------|
| Speech to text | `faster_whisper`, `vosk`, `elevenlab_stt`, `asr_confidence_selector` (pick between several recognizers), `whisper_stt`\*, `silero_vad`\* |
| Voice activity | `webrtc_vad` |
| Text to speech | `nao_tts`, `navel_tts`, `piper_tts`, `espeak-ng`, `sam_tts`, `elevenlab_tts` |
| LLM | `llm_service`, `llm_generate_on_trigger`, `llm_output_router`, `string_to_llm_append`, `token_accumulator`, `context_query`; older, one-shot versions: `llm_request`, `llm_stream` |
| Text processing | `regexp_modifier`, `str_sub`, `string_splitter`, `length_block`, `repeat_remover`, `english_lapsus`, `dark_lapsus` (French version) |
| NLP and knowledge graph | `spacy_ner`, `spacy_features`\*, `neo4j_request` |
| Flow control | `toggle_block`, `time_block`, `buffer`, `repeater`, `multiplexer`, `demultiplexer`, `queue_concat` |
| Operator | `woz_handler` |
| Testing | `dummy` |

\* currently fails to import, see [Known issues](#known-issues).

Other example configs in `configs/`: `dummy_config.json`, `echo_config.json`
(microphone to speaker), `basic_config.json` (keyboard and Vosk to console),
`bilingual_config.json` (French and English Vosk in parallel),
`service_config.json` (the LLM service with espeak-ng speech, without
meta-modules) and `test/` (port chaining, HTTP and NAO TTS tests).

## Writing a new module

1. Create `chatbot/<input|middle|output>_modules/<name>.py`. The file name
   is the module name used in configs.
2. Subclass `DummyInput`, `DummyMiddle` or `DummyOutput`, implement
   `action(self, i)`, and register the class in the file's dictionary
   (`input_modules_class`, `middle_modules_class` or `output_modules_class`,
   imported from the matching `dummy.py`):

```python
# chatbot/middle_modules/shout.py
from middle_modules.dummy import DummyMiddle, middle_modules_class
from utils.queues import QueueSlot

class Shout(DummyMiddle):
    """Upper-cases incoming strings. Optional second input: 'suffix'."""

    def __init__(self, name="shout", **args):
        super().__init__(name, **args)
        self._loop_type = 'thread'          # or 'process'
        self.datatype_in = 'string'
        self.datatype_out = 'string'
        self._input_queues['suffix'] = QueueSlot(self, 'input', datatype='string')
        self.suffix = args.get("suffix", "!")

    def action(self, i):
        text = self.input_queue.get()       # returns None when empty
        if text is None:
            return
        self.output_queue.put(text.upper() + self.suffix)

middle_modules_class['shout'] = Shout
```

3. Use it: `{"name": "s", "module": "middle_modules.shout", "args": {"suffix": "?"}}`,
   or `--middle shout`.

Tips:

- `get()` on a slot is non-blocking and returns `None` when nothing is
  available, so `None` can't be used as a signal; use a sentinel value (see
  `GENERATION_DONE` in `token_accumulator.py`).
- `action` runs in a tight loop; sleep briefly when idle (many modules take
  an `idle_sleep_s` or `delay` argument).
- `'process'` modules cannot share Python objects with the rest of the program;
  everything crosses queues, so data must be picklable.
- `utils.config.debug_print(...)` prints with `--verbose` and logs with `--log`.

## Repository layout

```
chatbot/
  main.py                    entry point
  input_modules/ middle_modules/ output_modules/
  utils/
    dummy_module.py          base class: slots, loops, linking
    queues.py                QueueWrapper, QueueSlot
    module_management.py     config loading, meta-module unrolling, validation
    config.py                debug_print, $ and @ argument processing
    http_server.py           shared HTTP servers keyed by (ip, port)
    llm_service/             context store, command dispatcher, streaming client, protocol
    darkcerveau.py, englishcerveau.py   phonetic-lapsus engines
    neo4j_utils.py, nao.py, spacy.py    helpers
configs/                     pipeline configs (see above)
misc/                        contexts, task data (poems, series), HTML templates, explanation text
tests/                       unit tests
prepare_repo.sh             dependency and model setup
download_models.sh          faster-whisper model cache (used by the Dockerfile)
run.sh, Dockerfile, requirements.txt
node-red_generator.sh       unfinished: generating Node-RED nodes from the modules
```

Generated and downloaded content (`venv/`, `models/`, `__pycache__/`) is
git-ignored. So is `misc/`, because `prepare_repo.sh` writes the FastText
model there: files already tracked in `misc/` are unaffected, but a **new**
file there needs `git add -f`.

## Tests

```bash
python -m unittest discover -s tests
```

(or `pytest tests`). Current coverage: `token_accumulator` and
`llm_generate_on_trigger`.

## Known issues

- `whisper_stt.py` and `silero_vad.py` contain syntax errors and
  `spacy_features.py` is an unimplemented stub (Python 2 `raise` syntax), so
  using those modules fails at import time. A config naming them passes
  `--test-config`, since that only checks that the file exists.
- `--test-config` validates structure only; it does not import modules, so
  missing dependencies or models appear only when the pipeline starts.
- `faster_whisper` defaults to `device: cuda`, `compute_type: float32`; set
  `device` and `compute_type` in `args` to run on a CPU.
- `QueueSlot.full()` is not implemented.
