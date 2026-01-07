#!/bin/bash

# The point of this script is to generate Node-RED nodes for each defined
# module in the chatbot directory.
# STATUS:
# - [x] Generate package.json file
# - [x] Generate nodes directory
# - [ ] Generate nodes (the hard one)

# Ensure we are in the correct directory
if [ ! -d "chatbot" ]; then
    echo "Error: 'chatbot' directory not found."
    exit 1
fi


mkdir -p ./node-red-chatbot-nodes

TARGET_FOLDERS="input_methods middle_methods output_methods"
TARGET_FOLDERS_MATCH="$(echo "$TARGET_FOLDERS" | tr ' ' '|')"

# List all files from which to create nodes
SOURCE_FILES=$(find chatbot/ -type f -printf "%p\n")
# Remove the "chatbot/" prefix from the file paths
SOURCE_FILES=${SOURCE_FILES//chatbot\//}
# Use grep to filter the input string
FILTERED_FILES=$(echo "$SOURCE_FILES" | tr ' ' '\n' | grep -w -E "$TARGET_FOLDERS_MATCH")

# Print the filtered string
#echo "$FILTERED_FILES"

NODE_NAMES=$(echo "$FILTERED_FILES" | tr '/' '_' | sed -e 's/\.py//' )
NODE_NAMES=(${NODE_NAMES})
NODE_FILES=$(echo "$FILTERED_FILES" | sed -e 's/^/nodes\//' | sed -e 's/.py/.js/')
NODE_FILES=(${NODE_FILES})
RANGE=${!NODE_NAMES[@]}
LEN=${#NODE_NAMES[@]}

FORMATTED=$(for i in $RANGE; do
    echo -n "        \"${NODE_NAMES[i]}\": \"${NODE_FILES[i]}\""
    if [ $i -ne $(($LEN-1)) ]; then
        echo ","
    else
        echo ""
    fi
    done)

# Generate the package.json file
echo """
{
  \"name\": \"node-red-chatbot-nodes\",
  \"node-red\": {
    \"nodes\": {
$(echo "$FORMATTED")
    }
  }
}
""" > node-red-chatbot-nodes/package.json

for folder in $TARGET_FOLDERS; do
    mkdir -p ./node-red-chatbot-nodes/nodes/$folder
done

