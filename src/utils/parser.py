"""
Author: Konano
Description: Parse HTTP request packet
"""

import traceback
from base64 import b64decode, b64encode
from pathlib import Path

import lark

from utils.log import logger

lark_parser = lark.Lark(
    Path("grammar/http_request.lark").read_text(), use_bytes=True, parser="lalr", debug=True
)

VERBOSE = False


def find_terminal(tree: lark.Tree, type: str, first_one=True):
    def judge(x):
        return isinstance(x, lark.Token) and x.type == type

    if first_one:
        return list(tree.scan_values(judge))[0].value
    else:
        return [x.value for x in tree.scan_values(judge)]


def find_rule(tree: lark.Tree, type: str, first_one=True):
    subtree = list(tree.find_data(type))[0]
    values = [x.value for x in subtree.scan_values(lambda x: isinstance(x, lark.Token))]
    return b"".join(values)


def parse(packet: bytes):
    try:
        tree = lark_parser.parse(packet)
        ret = {}
        ret["method"] = find_terminal(tree, "METHOD")
        ret["url"] = find_terminal(tree, "REQUEST_TARGET")
        ret["http_version"] = find_terminal(tree, "HTTP_VERSION")
        ret["headers"] = []
        for subtree in tree.find_data("field_line"):
            header_name = find_terminal(subtree, "FIELD_NAME")
            header_value = find_rule(subtree, "field_value")
            ret["headers"].append((header_name, header_value))
        ret["message_body"] = find_rule(tree, "message_body")
        if VERBOSE:
            print(tree.pretty())
        return ret
    except lark.exceptions.UnexpectedInput:
        logger.error("Unsuccess!")
        logger.error(traceback.format_exc())
        print(f"{b64encode(packet) = }")
    except Exception as e:
        logger.error(f"{e.__class__.__module__}.{e.__class__.__name__}: {e}")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    packet = b64decode(
        "R0VUIC9lYjMxZWFiYTllY2FkY2I5IEhUVFAvMS4xDQpIb3N0OiBhbGl5dW4tMS5uaXNsLmFjDQpWaWE6IGhrMjEubDEsIGVucy1jYWNoZTQuaGsyMSwgbDJoazIubDIsIGNhY2hlNC5sMmhrMg0KRWFnbGVleWUtVHJhY2VpZDogYTNiNTIyOWExNjQ4MTM4OTg0MDgwNTIzN2UNCkFsaS1Td2lmdC1Mb2ctSG9zdDogYWxpeXVuLTEubmlzbC5hYw0KQWxpLVN3aWZ0LVN0YXQtSG9zdDogbGV2ZWwyLmFsaXl1bi0xLm5pc2wuYWMNClgtRm9yd2FyZGVkLUZvcjogMjAyLjExMi41MS43OA0KWC1DbGllbnQtU2NoZW1lOiBodHRwDQpBbGktQ2RuLVJlYWwtSXA6IDIwMi4xMTIuNTEuNzgNCk9kYXRhLVZlcnNpb246IAk0LjAJDQpQcmFnbWE6IAk2ZDlmN2RmZTc3ZWIyMGVhDQpUb3BpYzogCSB1cGQNCkFsaS1UcHJveHktSHR0cGRuczogb24NCkFsaS1Td2lmdC01WHgtTm8tUmV0cnk6IG9uDQoNCg=="
    )
    logger.info(parse(packet))
