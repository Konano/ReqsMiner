"""
Author: Konano
Description: Differece analysis between the request received by the server and the request sent by the client
"""

import argparse

import pymongo

from utils.config import mongodb_cli
from utils.log import BANNER

db = pymongo.MongoClient(mongodb_cli)["reqsminer"]
db_reps = db["response"]


def get_args():
    parser = argparse.ArgumentParser(description="ReqsMiner Differece Analyser")

    parser.add_argument("-t", "--target", type=str, help="target host")
    parser.add_argument("--quiet", action="store_true", default=False, help="quiet mode")

    args = parser.parse_args()

    return args


if __name__ == "__main__":
    args = get_args()

    HOST = args.target
    QUIET = args.quiet

    filter = {}
    HOST is not None and filter.update({"host": HOST})

    print(BANNER)

    db_reps.count_documents(filter)

    resp_pair = []
    for x in db_reps.find(filter):
        resp_pair.append((
            x["server_len"], x["client_len"], x["token"], x["host"]
        ))
    resp_pair.sort(key=lambda x: x[0] / x[1], reverse=True)
    for x in resp_pair[:5]:
        print(f'Token: {x[2]}, ServerLen: {x[0]}, ClientLen: {x[1]}, AmpRatio: {x[0] / x[1]:.2f}')
