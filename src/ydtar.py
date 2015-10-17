#! /bin/python2
"""Source code for ydtar, the document formatting metalanguage system.

Read the docs/ directory for instructions.
Author: Timothy Hewitt
Date: 2015-10-16"""

import re
import yaml

###
# Trigger Defs
###



###
# Target Format Defs
###



###
# Main execution
###

def init_parser():
    

def main(trigger_file_name):
    init_parser() # add the constructors for triggers and targets
    with open(triggger_file_name, "r") as tfile:
        triggers = tfile.readlines().split("\n")


if __name__ == "__main__":
    from sys import argv
    main(argv[1]) # All ydtar cares about is the infile with triggers.
