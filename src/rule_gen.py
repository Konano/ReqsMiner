"""
Author: Konano
Description: ABNF Parser + Rule Fusioner
"""

import json
from pathlib import Path

from lark import Lark, Token, Tree

from utils.log import BANNER, logger

parser = Lark(Path("grammar/abnf.lark").read_text(), parser="lalr", debug=True)


def str_tree(tree: Tree):
    if tree.data == "clause":
        return str_tree(tree.children[0])
    elif tree.data == "clause_or":
        return " / ".join([str_tree(x) for x in tree.children])
    elif tree.data == "clause_and":
        return " ".join([str_tree(x) for x in tree.children])
    elif tree.data == "item":
        return tree.children[0].value
    elif tree.data == "values":
        return str_tree(tree.children[0])
    elif tree.data == "values_hex":
        values = [x.value + y.value for x, y in zip(tree.children[::2], tree.children[1::2])]
        return "%x" + ".".join(values)
    elif tree.data == "values_range_hex":
        values = [x.value + y.value for x, y in zip(tree.children[::2], tree.children[1::2])]
        return "%x" + "-".join(values)
    elif tree.data == "values_dec":
        values = [x.value for x in tree.children]
        return "%d" + ".".join(values)
    elif tree.data == "values_range_dec":
        values = [x.value for x in tree.children]
        return "%d" + "-".join(values)
    elif tree.data == "brackets_set":
        return str_tree(tree.children[0])
    elif tree.data == "brackets":
        return "( " + str_tree(tree.children[0]) + " )"
    elif tree.data == "brackets_01":
        return "[ " + str_tree(tree.children[0]) + " ]"
    elif tree.data.startswith("brackets_"):
        low, up = 0, -1
        for child in tree.children:
            if child.data == "item":
                item = str_tree(child)
            elif child.data == "clause":
                item = "( " + str_tree(child) + " )"
            elif child.data == "min":
                low = child.children[0].value
            elif child.data == "max":
                up = child.children[0].value
            elif child.data == "limit":
                low = up = child.children[0].value
            else:
                logger.error(f"NotImplementedType: {tree.data}")
        if low == up:
            return str(low) + item
        else:
            low = str(low) if low != 0 else ""
            up = str(up) if up != -1 else ""
            return low + "*" + up + item
    else:
        logger.error(f"NotImplementedType: {tree.data}")
    return ""


def print_rule(name: str, definition: Tree):
    text = str_tree(definition)
    if name in predefined:
        text += "".join([f' / "{x}"' for x in predefined[name]])
    dump_file.write(f"{name} = {text}\n")


def dfs(name: str):
    definition = rules[name]
    print_rule(name, definition)
    checked_rules.add(name)
    for token in definition.scan_values(lambda v: isinstance(v, Token)):
        if token.type == "TOKEN":
            if token.value not in rules:
                logger.error(f"NotFound: {token.value}")
            elif token.value not in checked_rules:
                dfs(token.value)


if __name__ == "__main__":
    rules = {}
    rfc = {}

    print(BANNER)

    # ========== read rfc rules ==========
    for file in Path("grammar/rfc").iterdir():
        rfc_id = file.name.split(".")[0]
        tree = parser.parse(file.open().read())
        for rule in tree.children:
            name, definition = rule.children
            if name not in rules:
                rules[name] = definition
                rfc[name] = rfc_id
            else:
                logger.warning(f'duplicate rule: "{name}" in RFC {rfc_id} and {rfc[name]}')

    # ========== read custom rules ==========
    tree = parser.parse(open("grammar/custom.abnf").read())
    for rule in tree.children:
        name, definition = rule.children
        name = name.replace("_", "-")
        rules[name] = definition

    # ========== read predefined data ==========
    predefined = json.load(open("grammar/predefined.json", "r"))
    for k in predefined.keys():
        predefined[k] = [x.replace('"', '\\"') for x in predefined[k]]

    # ========== combine rules ==========
    checked_rules = set()
    with open("grammar/http.abnf", "w") as dump_file:
        dfs("start")

    # ========== debug mode ==========
    # custom_name_set = set()
    # tree = parser.parse(open('grammar/custom.abnf').read())
    # for rule in tree.children:
    #     name, _ = rule.children
    #     custom_name_set.add(name)
    # for name in rules:
    #     if name not in checked_rules:
    #         if name in custom_name_set:
    #             print(name)
