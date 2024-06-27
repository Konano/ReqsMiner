"""
Author: Konano
Description: Extract the raw request from the database
"""

import sys

import pymongo

from utils.config import mongodb_cli


def bytes2str(b):
    return eval(str(b)[1:])


db = pymongo.MongoClient(mongodb_cli)["reqsminer"]
db_reqs = db["request"]
db_reps = db["response"]
db_diff = db["diff"]


def print_request(token):
    for x in db_reqs.find({"token": token}):
        print("===================== request - client =====================")
        print(bytes2str(x["client"]))
        print("===================== request - server =====================")
        print(bytes2str(x["server"]))


def print_response(token):
    for x in db_reps.find({"token": token}):
        if x.get("server"):
            print("===================== response - server =====================")
            print(bytes2str(x["server"]))
        if x.get("client"):
            print("===================== response - client =====================")
            print(bytes2str(x["client"]))


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1].isalnum():
        token = sys.argv[1]
        print(f'Token: {token}')
        print_request(token)
        print_response(token)
        print("===================== end =====================")
        exit()
    try:
        while True:
            token = input("Token: ").strip()
            print_request(token)
            print_response(token)
            print("===================== end =====================")
            print()
    except KeyboardInterrupt:
        pass
