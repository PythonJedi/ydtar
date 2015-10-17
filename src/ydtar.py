#! /bin/python2
"""Source code for ydtar, the document formatting metalanguage system.

Read the docs/ directory for instructions.
Author: Timothy Hewitt
Date: 2015-10-16"""

import re, os
import yaml

init = {}
targets = {}
documents = {}

###
# Util Defs
###
def pre_proc(string):
    """Add all the YAML docs in string to the proper library"""
    docs = re.split(r"^(?<=---\n)(\S+):", re.MULTILINE)
    assert "---\n" == docs[0]
    for i in range(1, len(docs)-1, 3):
        if docs[i+1].startswith("!target")
            targets[docs[i]] = "---\n" + docs[i]+docs[i+1]
        else:
            documents[docs[i]] = "---\n" + docs[i]+docs[i+1]

###
# Trigger Defs
###
def load(loader, node):
    fn = loader.construct_scalar(node)
    with open(os.path.normpath(fn), "r") as f:
        pre_proc(f.readlines)
init["!load"] = load

def build(loader, node):
    data = loader.load_mapping(node)
    if data["target"] in targets and data["document"] in documents:
        out = yaml.parse_all(targets[data["target"]]+documents[data["document"]])
        with open(os.path.normapth(data["out"]), "w") as of:
            of.write(out[data["document"]])
init["!build"] = build

###
# Target Format Defs
###



###
# Main execution
###

def init_parser():
    for tag in init:
        yaml.add_constructor(tag, init[tag])

def main(trigger_file_name):
    init_parser() # add the constructors for triggers and targets
    with open(triggger_file_name, "r") as tfile:
        triggers = tfile.readlines()
    yaml.load_all(triggers)


if __name__ == "__main__":
    from sys import argv
    main(argv[1]) # All ydtar cares about is the infile with triggers.
