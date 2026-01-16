# DISCOBOT: Designing an LLM powered user-centered knowledge graph for social robots to mitigate loneliness among university students

This is the repository for Lab-STICC DISCOBOT project for social robotics.  The
goal is a modular system that allows for easy creation of chatbot pipelines,
focusing on the "Navel" robot from navel robotics GmbH.

The project is currently in development, and contributions are welcome.

## Installation

### Linux

Installation presumes a `python` or `python3` install, with functional `pip`.

Once the repo is cloned, run the following.
```bash
./prepare_repo.sh
```
This should install the required dependencies, and download the required models.

### Windows

Not set up right now, would be a welcome contribution.

## Usage

The project is structured as a set of modules each contained within a file.

We expect three types of modules: 
1. input (takes data from outside the system, and thus has no "input" queues),
2. middle (takes data from within the system, and has both "input" and "output"
queues)
3. output (takes data from within the system, and thus has no "output" queues).

After activating the virtual environment with
```bash
source venv/bin/activate
```
you can run the main file with
```bash
python chatbot/main.py --help
```

You can either provide a simple, input-middle-output pipeline using command
line arguments, for instance
```bash
python chatbot/main.py --input-module input_modules/stdin.py --middle-module middle_modules/repeater.py --output-module output_modules/stdout.py
```
or use a configuration file, for instance
```bash
python chatbot/main.py --config basic_config.json
```

Config files are json files containing a list of modules and links between 
them in a simplistic in-to-out format.

## Structure

Each type of module is contained in a separate directory, and each module is
contained in a separate file.

Each of these modules inherit from their directory's "dummy" module class,
which provides a basic structure for the module.

```bash
chatbot/
├── main.py         # Main file
├── input_modules   # Modules with output queues and no input queues
├── middle_modules  # Modules with input and output queues
├── output_modules  # Modules with input queues and no output queues
└── utils           # Non-module utilities and prototypes
```

## Progress

How far along is the project?

Minimal viable product is:
* Input modules: 
    - Audio input (Done, implementations with pyaudio and sounddevice)
    - Keyboard input
* Middle modules: 
    - Speech to text (Done, using Vosk)
    - Database polling (TODO)
    - Language model (Done, using OpenAI API)
* Output modules: 
    - Text to speech (Done, using Navel TTS)
    - Database update (TODO)

Other desirable features:
* Input modules:
    - STDIN
    - Vision input  (TODO)
* Middle modules: 
    - Alternative, lightweight NLP modules (TODO)
* Output modules: 
    - STDOUT
    - Alternative TTS modules (TODO)

Contributions are welcome!  Clone the repo, make your changes, and submit 
a pull request.
