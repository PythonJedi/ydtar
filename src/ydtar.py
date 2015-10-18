#! /bin/python2
"""Source code for ydtar, the document formatting metalanguage system.

Read the docs/ directory for instructions.
Author: Timothy Hewitt
Date: 2015-10-16"""

import re, os, datetime
import yaml

init = {}
targets = {}
documents = {}
segments = {}
env = {}

###
# Util Defs
###
def pre_proc(string):
    """Add all the YAML docs in string to the proper library"""
    docs = re.split("^(?<=---\n)(\S+)\s*:", string, 0, re.MULTILINE)
    assert "---\n" == docs[0]
    for i in range(1, len(docs)-1, 3):
        if re.match("^\s*!target", docs[i+1]):
            print "Adding Target: " + docs[i]
            targets[docs[i]] = "---\n" + docs[i]+": "+ docs[i+1]
        else:
            print "Adding Document: " + docs[i]
            documents[docs[i]] = "---\n" + docs[i]+": " + docs[i+1]

def find(name, data):
    #print "finding "+repr(name)+" in "+repr(data)
    if name:
        name, sep, nxt = name.partition(".")
        if isinstance(data, list):
            if not name.isdigit():
                data = env
            else:
                name = int(name)
        elif name not in data:
            data = env
        ret = find(nxt, data[name])
        #print "find returning " +  repr(ret)
        return ret
    else:
        #print "find returning " +  repr(data)
        return data

def get_date():
    dat = datetime.date.today()
    return "-".join(map(str, (dat.year, dat.month, dat.day)))

###
# Trigger Defs
###
def load(loader, node):
    fn = loader.construct_scalar(node)
    with open(os.path.normpath(fn), "r") as f:
        pre_proc("".join(f.readlines()))
init["!load"] = load

def build(loader, node):
    global env
    data = loader.construct_mapping(node, deep=True)
    if data["target"] in targets and data["document"] in documents:
        yaml.load(targets[data["target"]])
        env = {"_date": get_date(), "_level": dict([(s, 0) for s in segments.values()])}
        out = yaml.load(documents[data["document"]])
        with open(os.path.normpath(data["out"]), "w") as of:
            of.write(out[data["document"]])
    else:
        print "No such target "+ data["target"] + " or document " + data["document"]
init["!build"] = build

###
# Target Format Defs
###
def target(loader, node):
    """targets are a mapping of names to segment formatter directives."""
    data = loader.construct_mapping(node, deep=True)
    for t in data:
        yaml.add_constructor("!"+t, data[t])
        segments[data[t]] = t
        print "Loaded segment: "+t
init["!target"] = target

def segment(loader, node):
    """segment actually constructs a formatter"""
    data = loader.construct_sequence(node, deep=True)
    def fmt(loader, node):
        global env
        string = ""
        # print "segment "+segments[fmt]+" applied to "+repr(node)
        old_lev = env["_level"][segments[fmt]]
        env["_level"][segments[fmt]] += 1
        for item in data:
            if not isinstance(item, str):
                item = item(loader, node)
            string += item
        env["_level"][segments[fmt]] = old_lev
        return string
    return fmt
init["!segment"] = segment

def ref(loader, node):
    """ref gets a value from the node or the env"""
    name = loader.construct_scalar(node)
    def fmt(loader, node):
        #print "!ref'ing "+repr(name) + " in "+repr(node) + "\n  with loader "+repr(loader)
        if loader:
            data = None
            try:
                data = loader.construct_mapping(node, deep=True)
            except yaml.YAMLError, exc:
                #print "Could not construct mapping from "+str(node.__class__)
                try:
                    data = loader.construct_sequence(node, deep=True)
                except yaml.YAMLError, exc:
                    #print "Could not construct sequence from "+str(node.__class__)
                    try:
                        data = loader.construct_scalar(node)
                    except yaml.YAMLError, exc:
                        pass
                        #print "Could not construct scalar from "+str(node.__class__)
            if not data:
                raise ValueError("invalid node type! " + str(node.__class__))
            if isinstance(data, str):
                return data
        else:
            data = node
        #print "  which constructed "+repr(data)
        d = find(name, data)
        #print "  and therefore found "+repr(d)
        return d
    return fmt
init["!ref"] = ref

def per_item(loader, node):
    ins = loader.construct_mapping(node, deep=True)
    def fmt(loader, node):
        string = ""
        if loader:
            node = ins["in"](loader, node) # Top level formatting
        #print "!per-item in "+repr(node)
        if isinstance(node, list):
            for item in node:
                string += ins["do"](None, item)
        if isinstance(node, dict):
            for item in [[k, node[k]] for k in node]:
                #print "formatting item in dict " + repr(item)
                string += ins["do"](None, item)
        return string
    return fmt
init["!per-item"] = per_item

def repeat(loader, node):
    ins = loader.construct_sequence(node, deep=True)
    def fmt(loader, node):
        if isinstance(ins[1], int):
            if isinstance(ins[0], str):
                return ins[1]*ins[0]
            else:
                return ins[1]*ins[0](loader, node)
        else:
            if isinstance(ins[0], str):
                return ins[1](loader, node)*ins[0]
            else:
                return ins[1](loader, node)*ins[0](loader, node)
    return fmt
init["!repeat"] = repeat

def cat(loader, node):
    ins = loader.construct_sequence(node, deep=True)
    def fmt(loader, node):
        string = ""
        #print "!cat'ing "+str(ins)
        for item in ins:
            if not isinstance(item, (str, int)):
                item = item(loader, node)
            string += str(item)
        return string
    return fmt
init["!cat"] = cat

def repl(loade, node):
    ins = loader.construct_mapping(node, deep=True)
    def fmt(loader, node):
        string = ins["in"](loader, node)
        for pat in ins["by"]:
            re.sub(pat, ins["by"][pat], ins["in"])
        return string
    return repl
init["!repl"] = repl

def indent(loader, node):
    m = loader.construct_mapping(node, deep=True)
    ind = m["by"]
    def fmt(loader, node):
        string = ""
        data = m["data"](loader, node)
        #print "!indenting "+repr(data)+" by "+repr(ind)
        if isinstance(data, list):
            data = "".join(data)
        for line in data.splitlines(True):
            string += ind + line
        return string
    return fmt
init["!indent"] = indent


def set(loader, node):
    ins = loader.construct_mapping(node, deep=True)
    def fmt(loader, node):
        env.update(ins)
        return ""
    return fmt
init["!set"] = set

def sum(loader, node):
    ins = loader.construct_seq(node)
    def fmt(loader, node):
        val = 0
        for item in ins:
            if not isinstance(item, (int)):
                item = item(loader, node)
            val += item
        return val
    return fmt
init["!sum"] = sum

def mul(loader, node):
    ins = loader.construct_seq(node)
    def fmt(loader, node):
        val = 0
        for item in ins:
            if not isinstance(item, (int)):
                item = item(loader, node)
            val *= item
        return val
    return fmt
init["!mul"] = mul

###
# Main execution
###

def init_parser():
    for tag in init:
        yaml.add_constructor(tag, init[tag])

def main(trigger_file_name):
    init_parser() # prep the parser to handle triggers and targets
    with open(trigger_file_name, "r") as tfile:
        triggers = "".join(tfile.readlines())
    yaml.load(triggers)


if __name__ == "__main__":
    from sys import argv
    main(argv[1]) # All ydtar cares about is the infile with triggers.
