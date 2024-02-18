"""
Author: Konano
Description: Extract the raw request from the database
"""

import pymongo

from utils.config import mongodb_cli


def bytes2str(b):
    return eval(str(b)[1:])


db = pymongo.MongoClient(mongodb_cli)["reqs-miner"]
db_reqs = db["request"]
db_diff = db["diff"]


def print_request(token):
    for x in db_reqs.find({"token": token}):
        print("===================== client =====================")
        print(bytes2str(x["client"]))
        print("===================== server =====================")
        print(bytes2str(x["server"]))


while True:
    token = input("Token: ").strip()
    print_request(token)
