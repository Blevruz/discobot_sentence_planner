# ARCHITECTURE

## Multithreaded structure

Thread for speech to text
Other user input?
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
