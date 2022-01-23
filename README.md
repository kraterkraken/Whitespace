# Whitespace
An interpretter for Edwin Brady's and Chris Morris's [Whitespace esoteric programming language](https://en.wikipedia.org/wiki/Whitespace_(programming_language)).  Written in Python3.

### Usage
```
whitepsace.py - execute a program in the Whitespace programming language

usage: whitespace.py [--debug] filename
usage: whitespace.py [--debug] --test
usage: whitespace.py --help

Options:
  filename                An input file containing Whitespace code
  --test                  Runs unit tests (overrides filename)
  --debug                 Turns on verbose debugging
  --help                  Prints this help info
```

### Test Programs Included
I've included several test programs that I found on the interet.  Some work, some don't.  As far as I can tell, this is what they are supposed to do.
-cat.ws - Silently prompts user for input, and simply repeats what the user typed
-count10.ws - Prints the numbers from 1 to 10
-greet.ws - Asks use for their name and prints it
-hworld.ws - Hello world program
-truth.ws - Silently prompts user for input.  If 0, it prints 0 and exits.  If not zero, prints infinite 1's.

