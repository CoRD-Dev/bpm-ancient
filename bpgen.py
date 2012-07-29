#!/usr/bin/env python3
# -*- coding: utf8 -*-
################################################################################
##
## Copyright (C) 2012 Typhos
##
## This Source Code Form is subject to the terms of the Mozilla Public
## License, v. 2.0. If a copy of the MPL was not distributed with this
## file, You can obtain one at http://mozilla.org/MPL/2.0/.
##
################################################################################

import argparse
import re
import sys
import time

import yaml

# TODO: Change the way this all works.
#    - Load all YAML files. Discard the emotes specified in the master config.
#    - Flatten the CSS. Go from top-down according to classes (eventually).
#      We can do this simply- each "object" (make them objects) at each tier
#      has a css_props variable. Merge them downward.
#    - Separate NSFW emotes out.
#    - Compress according to whatever rules we like. Since we've just split
#      stuff out, we can't do it from the original YAML files via "classes".
#      Instead, try to make it smart, or something.

def process_file(filename, data, css_rules, js_map, seen):
    for (image_url, emotes) in data.pop("Spritesheets", {}).items():
        process_spritesheet(css_rules, js_map, image_url, emotes, seen)

    for (name, props) in data.pop("Custom", {}).items():
        selector = format_selector(name)
        assert (selector,) not in css_rules

        if name in js_map:
            assert js_map[name] == selector.lstrip(".")

        for (k, v) in props.items():
            # Make sure they're all strings, as they should be. YAML sometimes
            # converts things we don't want it to (integers), but for custom
            # CSS we just assume everything's a string.
            props[k] = str(v)
        css_rules[(selector,)] = props

        # Another quick hack
        if ":" in name:
            name = name[:name.index(":")]
        if ":" in selector:
            selector = selector[:selector.index(":")]

        js_map[name.lower()] = selector.lstrip(".")

    for section in data:
        print("WARNING: Unknown section %s in %s" % (section, filename))

CommonCss = {"display": "block", "clear": "none", "float": "left"}

def process_spritesheet(css_rules, js_map, image_url, emotes, seen):
    selectors = {}

    for (name, props) in emotes.items():
        process_emote(name, props, selectors, css_rules, js_map, seen)

    mega_selector = tuple(selectors.values())
    if mega_selector not in css_rules: # Might be, sometimes, for single-emote sheets
        css_rules[mega_selector] = {}

    css_rules[mega_selector].update({
        "display": "block",
        "clear": "none",
        "float": "left",
        "background-image": "url(%s)" % (image_url)
        })

def process_emote(name, props, selectors, css_rules, js_map, seen):
    if name in seen:
        raise Exception("CONFLICT:", name)
    seen.add(name)

    assert name.startswith("/")
    selector = format_selector(name)

    if not overrides_bg(name, props):
        selectors[name] = selector

    (width, height, x_pos, y_pos) = props.pop("Positioning")

    css_rules[(selector,)] = {
        "width": px(width),
        "height": px(height),
        "background-position": "%s %s" % (px(x_pos), px(y_pos))
        }

    if "Extra CSS" in props:
        css_rules[(selector,)].update(props.pop("Extra CSS", {}))

    for (key, val) in props.items():
        print("WARNING: Unknown property %r on %s in (%r)" % (
            key, name, val))

    if not is_special(name):
        js_map[name.lower()] = selector.lstrip(".")

def overrides_bg(name, props):
    if is_special(name):
        if "background-image" in props:
            return True
    return False

def is_special(name):
    return name.endswith(":hover") or name.endswith(":active")

def px(s):
    return "%spx" % (s)

def format_selector(name):
    assert name.startswith("/")
    # Quick hack (can't replace : with _ unconditionally because of :hover and
    # such. FIXME)
    if name == "/pp:3":
        name = "/pp_3"
    # Argh
    name = name.replace("!", "_excl_")
    return ".bpmotes-%s" % (name.lstrip("/"))

AutogenHeader = """
/*
 * This file is AUTOMATICALLY GENERATED. DO NOT EDIT.
 * Generated at %s.
 */

""" % (time.strftime("%c"))

def dump_css(file, rules):
    file.write(AutogenHeader)

    for (selectors, properties) in rules.items():
        file.write("%s\n" % (format_rule(selectors, properties)))

def format_rule(selectors, properties):
    for (key, val) in properties.items():
        if not isinstance(val, str):
            raise ValueError("non-string key", key)

    props_string = "; ".join(("%s: %s" % (prop, value)) for (prop, value) in properties.items())
    return "%s { %s }" % (", ".join(selectors), props_string)

def dump_js(file, map):
    file.write(AutogenHeader)
    file.write("var emote_map = {\n")

    strings = ["    %r: %r" % (emote.lower(), css_class.lstrip(".")) for (emote, css_class) in map.items()]
    file.write(",\n".join(strings))

    file.write("\n}\n")

def main():
    parser = argparse.ArgumentParser(description="Generates BetterPonymotes's data files from a set of YAML inputs")
    parser.add_argument("--css", help="Output CSS file", type=argparse.FileType("w"), default="emote_classes.css")
    parser.add_argument("--js", help="Output JS file", type=argparse.FileType("w"), default="data/emote_map.js")
    parser.add_argument("yaml", help="Input YAML files", type=argparse.FileType("r"), nargs="+")
    args = parser.parse_args()

    css_rules = {}
    js_map = {}
    seen = set()

    for file in args.yaml:
        process_file(file.name, yaml.load(file), css_rules, js_map, seen)

    dump_css(args.css, css_rules)
    dump_js(args.js, js_map)

if __name__ == "__main__":
    main()
