#!/bin/bash
if [ "$1" == "--debug" ]
  then
    ARGS="${@:2}"
    PYTHON="pdb"
  else
    ARGS="$@"
    PYTHON="python"
fi
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHONPATH_LIBS="$(find $DIR -name '*.egg' -print0 | tr "\0" ":")" # NOTE: This is includes trailing :
SUPPORT_DIR="${DIR}/support"

PYTHONPATH="${PYTHONPATH_LIBS}${SUPPORT_DIR}:$PYTHONPATH" exec $PYTHON $ARGS

