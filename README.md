# ARCHITECTURE

## Modularity

It is preferable for all modules to be independent, and for the user to choose
which modules to use when running the program.  Choice of modules is handled by
argparse in chatbot/main.py.  Ideally, multiple modules achieving the same
functionality should be able to be used simultaneously for confidence
estimation. (e.g. do levenshtein distance between multiple STT)

### Planned Modules:
* Input:    (WIP)
    * Dummy (Hello Worlds at regular intervals)
    * Speech to text  (WIP)
    1. Vosk         (rough draft)
    2. Whisper      (TODO)
    * Keyboard input
    * Pipe in
* Output:
    * Dummy (prints to console)
    * Text to speech
    1. Navel TTS
    * Pipe out
* Storage:  (TODO)
    * Dummy           (TODO)
    * File            (TODO)
    * Neo4j           (TODO)
* NLP:  (TODO)
    * Dummy           (TODO)
    * Language model  (TODO)
    * SpaCy           (TODO)
    * Stanza          (TODO)
* Sentence generation:  (TODO)
    * Dummy           (TODO)
    * Language model  (TODO)
    * Graph?          (TODO)
* Body language:    (TODO)
    * Dummy           (TODO)
    * Face            (TODO)
    * Gaze            (TODO)
    * Body?           (TODO)
* Perception:   (TODO)
    * Dummy           (TODO)
    * Vision          (TODO)
    * Audio           (TODO)

### Module Structure

All modules are composed of a set of input queues, a set of output queues, and 
a loop function.  A module can only read from its input queues, and can only write
to its output queues.  Each queue is unique to a pair of modules.


### Layout Storage

Currently, layouts are entirely managed by `chatbot/main.py` for testing.
Modules are selected by command line arguments.  Available modules can be
listed by running `chatbot/main.py --help`.


## Multithreaded structure

Thread for speech to text
Other user input:
    Keyboard input needs to be on main thread, as should printing/logging
Thread for sentence planning
    Needs to use history to plan sentences
        Read-only queue from input thread
    Poll database for relevant info?
    Prompt language model for generated sentence


## Prompt structure

Ability to identify a number of features on request
    Named entities?
    Subject/Verb/Object triplets?
    Eventual train of thoughts
    And of course the generated sentence

Formulate response as a json object

## Database

Store information about user
Store information about the agent as another user
