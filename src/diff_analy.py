"""
Author: Konano
Description: Differece analysis between the request received by the server and the request sent by the client
"""

import argparse

import pymongo
from rich.progress import track

from utils.config import mongodb_cli
from utils.diff import Diff, DiffType, DiffTypeName
from utils.log import BANNER, logger

# from utils import bytes2str


db = pymongo.MongoClient(mongodb_cli)["reqs-miner"]
db_reqs = db["request"]
db_diff = db["diff"]


def get_args():
    parser = argparse.ArgumentParser(description="ReqsMiner Differece Analyser")

    parser.add_argument("-t", "--target", type=str, help="target host")
    parser.add_argument("-f", "--field", type=str, help="field to be compared")
    parser.add_argument(
        "--type",
        type=str,
        help=f"type of difference (0-6 / {', '.join(DiffTypeName)})",
    )
    parser.add_argument("--quiet", action="store_true", default=False, help="quiet mode")

    args = parser.parse_args()
    if args.type is not None:
        if args.type.isdigit() and 0 <= int(args.type) <= 6:
            args.type = int(args.type)
        elif args.type in DiffTypeName:
            args.type = DiffType[args.type].value
        else:
            parser.print_help()
            exit()

    return args


if __name__ == "__main__":
    args = get_args()

    HOST = args.target
    FIELD = args.field
    TYPE = args.type
    QUIET = args.quiet

    filter = {}
    HOST is not None and filter.update({"host": HOST})
    FIELD is not None and filter.update({"field": FIELD})
    TYPE is not None and filter.update({"type": TYPE})

    print(BANNER)

    diffs = set()
    total = db_diff.count_documents(filter)
    if QUIET:
        for x in db_diff.find(filter):
            diffs.add(
                Diff(
                    DiffType(x["type"]),
                    x["field"],
                    x["before"],
                    x["after"],
                    x["token"],
                    x["host"] if HOST is None else "",
                )
            )
    else:
        for x in track(db_diff.find(filter), total=total):
            diffs.add(
                Diff(
                    DiffType(x["type"]),
                    x["field"],
                    x["before"],
                    x["after"],
                    x["token"],
                    x["host"] if HOST is None else "",
                )
            )
        logger.info(f"{len(diffs) = }")

    if FIELD is None and TYPE is None:
        field_type = {}
        if QUIET:
            for d in diffs:
                field_type[d.field] = field_type.get(d.field, 0) | (1 << d.type)
        else:
            for d in track(diffs):
                field_type[d.field] = field_type.get(d.field, 0) | (1 << d.type)
        type_collect = {}
        for field, type_col in field_type.items():
            if type_col not in type_collect:
                type_collect[type_col] = []
            type_collect[type_col].append(field)
        for type_col in sorted(type_collect.keys()):
            print([x.name for x in DiffType if (type_col >> x) & 1], sorted(type_collect[type_col]))

    else:
        for x in diffs:
            print(x)

        # Overwrite
        _value = set()
        for x in diffs:
            if x.type in [DiffType.Modify, DiffType.Add]:
                _value.add(x.after)
            elif x.type in [DiffType.Retain]:
                _value.add(x.before)
        if len(_value) == 1:
            print(f"Overwrite: {_value.pop()}")
        # else:
        #     print(_value)
