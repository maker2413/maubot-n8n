#!/bin/sh

FILE="n8nagent.mbp"

# If the file exists, delete it
if [ -f "$FILE" ]; then
    rm "$FILE"
fi

# Run the zip command
zip -q -9r "$FILE" maubot.yaml n8nagentbot base-config.yaml
