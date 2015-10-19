#! /usr/bin/python2
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
    docs = re.split("^(---\n)\s*(\S+)\s*:", string, 0, re.MULTILINE)
    for i in range(2, len(docs)-1, 3):
        if re.match("^\s*!target", docs[i+1]):
            print "Adding Target: " + docs[i]
            targets[docs[i]] = "---\n" + docs[i]+": "+ docs[i+1]
        else:
            print "Adding Document: " + docs[i]
            #print string
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
        print "Building "+data["document"]+" with target spec "+data["target"]+ " to "+data["out"]
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
    def seg_fmt(loader, node):
        global env
        string = ""
        #print "segment "+segments[seg_fmt]+" applied to "+repr(type(node))
        old_lev = env["_level"][segments[seg_fmt]]
        env["_level"][segments[seg_fmt]] += 1
        for item in data:
            if not isinstance(item, str):
                item = item(loader, node)
            string += item
        env["_level"][segments[seg_fmt]] = old_lev
        #print "  segment "+segments[seg_fmt]+" produced "+repr(string)
        return string
    return seg_fmt
init["!segment"] = segment

def ref(loader, node):
    """ref gets a value from the node or the env"""
    name = loader.construct_scalar(node)
    def ref_fmt(loader, node):
        #print "!ref'ing "+repr(name) + " in "+repr(node)[:50]
        #print "  with loader "+repr(loader)
        data = None
        if loader:
            #print "  Loader valid, loading node "+str(node.__class__)
            try:
                data = loader.construct_mapping(node, deep=True)
                #print "  Valid Loader loaded "+str(node.__class__)+" as "+repr(data)
            except yaml.YAMLError, exc:
                #print "  Could not construct mapping from "+str(node.__class__)
                #print str(exc)
                try:
                    data = loader.construct_sequence(node, deep=True)
                except yaml.YAMLError, exc:
                    #print "  Could not construct sequence from "+str(node.__class__)
                    try:
                        data = loader.construct_scalar(node)
                    except yaml.YAMLError, exc:
                        pass
                        #print "  Could not construct scalar from "+str(node.__class__)
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
    return ref_fmt
init["!ref"] = ref

def per_item(loader, node):
    ins = loader.construct_mapping(node, deep=True)
    def per_item_fmt(loader, node):
        string = ""
        node = ins["in"](loader, node)
        #print "!per-item in "+repr(node)
        if isinstance(node, list):
            for item in node:
                string += ins["do"](None, item)
        if isinstance(node, dict):
            for item in [[k, node[k]] for k in node]:
                #print "formatting item in dict " + repr(item)
                string += ins["do"](None, item)
        return string
    return per_item_fmt
init["!per-item"] = per_item

def repeat(loader, node):
    ins = loader.construct_sequence(node, deep=True)
    def repeat_fmt(loader, node):
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
    return repeat_fmt
init["!repeat"] = repeat

def cat(loader, node):
    ins = loader.construct_sequence(node, deep=True)
    def cat_fmt(loader, node):
        string = ""
        #print "!cat'ing "+str(ins)
        for item in ins:
            if not isinstance(item, (str, int)):
                #print "  "+str(item)+"(loader, node) produces:"
                item = item(loader, node)
                #print "    "+str(item)
            #assert isinstance(item, str)
            #print "  Appending "+repr(item)
            string += str(item)
        #print "  to produce "+repr(string)
        return string
    return cat_fmt
init["!cat"] = cat

def repl(loader, node):
    ins = loader.construct_mapping(node, deep=True)
    def repl_fmt(loader, node):
        string = ins["in"](loader, node)
        if isinstance(string, list):
            string = "".join(string)
        for pat in ins["by"]:
            val = ins["by"][pat]
            if not isinstance(val, str):
                val = val(loader, node)
            #print "!repl'ing '"+pat+"' with '"+val+"' in '"+string+"'"
            string = re.sub(pat, val, string)
            #print "  Got "+string
        return string
    return repl_fmt
init["!repl"] = repl

def indent(loader, node):
    m = loader.construct_mapping(node, deep=True)
    ind = m["by"]
    def indent_fmt(loader, node):
        string = ""
        data = m["data"](loader, node)
        #print "!indenting "+repr(data)+" by "+repr(ind)
        if isinstance(data, list):
            data = "".join(data)
        for line in data.splitlines(True):
            string += ind + line
        return string
    return indent_fmt
init["!indent"] = indent


def set(loader, node):
    ins = loader.construct_mapping(node, deep=True)
    def set_fmt(loader, node):
        for n in ins:
            val = ins[n]
            if not isinstance(val, (int, str)):
                val = val(loader, node)
            env[n] = val
        return ""
    return set_fmt
init["!set"] = set

def sum(loader, node):
    ins = loader.construct_seq(node)
    def sum_fmt(loader, node):
        val = 0
        for item in ins:
            if not isinstance(item, (int)):
                item = item(loader, node)
            val += item
        return val
    return sum_fmt
init["!sum"] = sum

def mul(loader, node):
    ins = loader.construct_seq(node)
    def mul_fmt(loader, node):
        val = 0
        for item in ins:
            if not isinstance(item, (int)):
                item = item(loader, node)
            val *= item
        return val
    return mul_fmt
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
