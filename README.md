# ARCHITECTURE

## Modularity

It is preferable for all modules to be independent, and for the user to choose
which modules to use when running the program.  Choice of modules is handled by
argparse in chatbot/main.py.  Ideally, multiple modules achieving the same
functionality should be able to be used simultaneously for confidence
estimation. (e.g. do levenshtein distance between multiple STT)

Modules:
    Input:
        Dummy (Hello Worlds at regular intervals)
        Speech to text  (TODO)
            Vosk        (WIP)
            Whisper     (TODO)
        Keyboard input
        Pipe in?        (TODO)
    Output:
        Dummy (prints to console)
        Text to speech  (TODO)
        Pipe out?       (TODO)
    Storage:
        Dummy           (TODO)
        File            (TODO)
        Neo4j           (TODO)
    NLP:
        Dummy           (TODO)
        Language model  (TODO)
        SpaCy           (TODO)
        Stanza          (TODO)
    Sentence generation:
        Dummy           (TODO)
        Language model  (TODO)
        Graph?          (TODO)
    Body language:
        Dummy           (TODO)
        Face            (TODO)
        Gaze            (TODO)
        Body?           (TODO)
    Perception:
        Dummy           (TODO)
        Vision          (TODO)
        Audio           (TODO)







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
