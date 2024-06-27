"""
Author: Konano
Description: generate HTTP request and send it to CDNs, then compare the request received by the server with the request sent by the client, and store the difference analysis result in the database
"""

import argparse
import os
import pickle
import queue
import random
import re
import socket
import threading
from base64 import b64decode, b64encode
from concurrent.futures import ThreadPoolExecutor
from os import urandom
from pathlib import Path

import pymongo
from rich.progress import Progress

from utils.config import mongodb_cli
from utils.diff import diff_analy
from utils.generator import Tree
from utils.log import BANNER, error_handler, logger

WORKER_NUM = 100

ROUND_NUM = 100
ROUND_SIZE = 100  # generate requests per round

PACKET_MAXSIZE = 1024

SOCKET_FIRST_TIMEOUT = 5
SOCKET_CONTINUE_TIMEOUT = 1

MCTS_MODE = True


# ====================================================================================================


lock = threading.Lock()


class BoundThreadPoolExecutor(ThreadPoolExecutor):
    def __init__(self, *args, **kwargs):
        super(BoundThreadPoolExecutor, self).__init__(*args, **kwargs)
        self._work_queue = queue.Queue(16)


db = pymongo.MongoClient(mongodb_cli)["reqsminer"]
db_reqs = db["request"]
db_reps = db["response"]
db_diff = db["diff"]


def placeholder(packet: bytes, token: str) -> bytes:
    # __URL__ and __HOST__
    packet = packet.replace(b"__URL__", b"/reqsminer/" + token.encode())
    packet = packet.replace(b"__HOST__", HOST.encode())

    # __RANDOM__
    while b"__RANDOM__" in packet:
        packet = packet.replace(b"__RANDOM__", urandom(8).hex().encode(), 1)

    # __MESSAGE_BODY__ and __CONTENT_LENGTH__
    msg_len = 0
    if b"__MESSAGE_BODY__" in packet:
        msg_len = random.randint(1, 512)
        msg = urandom(msg_len)
        packet = packet.replace(b"__MESSAGE_BODY__", msg)
    packet = packet.replace(b"__CONTENT_LENGTH__", str(msg_len).encode())
    packet = packet.replace(b"__CONTENT_LENGTH_+1__", str(msg_len + 1).encode())
    packet = packet.replace(b"__CONTENT_LENGTH_-1__", str(msg_len - 1).encode())

    # __SEPARATES__
    packet = packet.replace(b"__SEPARATES__", urandom(8).hex().encode())

    return packet


def valid(packet: bytes) -> bool:
    token = urandom(8).hex()
    request_client = placeholder(packet, token)
    if len(request_client) > PACKET_MAXSIZE:
        return False

    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(SOCKET_FIRST_TIMEOUT)
            s.connect((HOST, 80))
            s.send(request_client)
        except socket.timeout:
            s.close()
            continue
        break
    try:
        response = b""
        s.settimeout(SOCKET_FIRST_TIMEOUT)
        try:
            buf = s.recv(1024)
        except socket.timeout:
            return False
        while len(buf):
            response += buf
            s.settimeout(SOCKET_CONTINUE_TIMEOUT)
            buf = s.recv(1024)
    except socket.timeout:
        pass

    try:
        # Corner Case: in Google Cloud CDN, ReqsMiner -> Reqsminer
        request_server = b64decode(
            re.findall(rb"(?<=ReqsMiner: )[a-zA-Z0-9+\/]+={0,2}(?=\r\n)", response)[0]
        )
    except Exception:
        return False

    try:
        diffs = diff_analy(request_client, request_server)
        if len(diffs):
            db_reqs.insert_one(
                {"token": token, "host": HOST, "client": request_client, "server": request_server}
            )
            db_diff.insert_many([x.dump_mongodb(token, HOST) for x in diffs])
        else:
            db_reqs.insert_one(
                {
                    "token": token,
                    "host": HOST,
                    "client": request_client,
                    "server": request_server,
                    "invalid_after": True,
                }
            )
        db_reps.update_one(
            {"token": token},
            {"$set": {"host": HOST, "client": response, "client_len": len(response)}},
            upsert=True
        )
        return True
    except Exception as e:
        error_handler(e)
        logger.debug(f"{b64encode(request_client) = }")
        logger.debug(f"{b64encode(request_server) = }")
        return False


def get_args():
    parser = argparse.ArgumentParser(description="ReqsMiner Client")

    parser.add_argument(
        "-t", "--target", type=str, default="localhost", help="target host (default: localhost)"
    )
    parser.add_argument("--thread-num", type=int, default=100, help="thread num (default: 100)")
    parser.add_argument("--round-num", type=int, default=100, help="round num (default: 100)")
    parser.add_argument("--round-size", type=int, default=100, help="round size (default: 100)")
    parser.add_argument(
        "--packet-maxsize", type=int, default=1024, help="packet maxsize (default: 1024)"
    )
    parser.add_argument(
        "--random", action="store_true", default=False, help="random mode (default: False)"
    )
    parser.add_argument(
        "--verbose", action="store_true", default=False, help="verbose mode (default: False)"
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = get_args()

    HOST = args.target
    WORKER_NUM = args.thread_num
    ROUND_NUM = args.round_num
    ROUND_SIZE = args.round_size
    PACKET_MAXSIZE = args.packet_maxsize
    MCTS_MODE = not args.random
    VERBOSE = args.verbose

    print(BANNER)

    t: Tree = Tree(Path(f"grammar/http.abnf").read_text(), MCTS_MODE)

    OUTPUT_DIR = f"data/{HOST}"
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    try:
        with open(f"{OUTPUT_DIR}/selector_history", "rb") as f:
            t.selector.history = pickle.load(f)
    except:
        t.selector.history = {}

    succ_num = 0
    round_num = 0
    running = True
    with Progress() as progress:
        __task = progress.add_task("Running...", total=ROUND_SIZE)

        def acquire_lock():
            while True:
                if not running:
                    raise KeyboardInterrupt
                if lock.acquire(timeout=1):
                    break

        def task():
            global succ_num, round_num, running

            try:
                acquire_lock()
                packet, records = t.generate()
            except KeyboardInterrupt:
                return
            except Exception as e:
                error_handler(e)
            finally:
                lock.locked() and lock.release()

            try:
                succ = valid(packet)
            except KeyboardInterrupt:
                return
            except (ConnectionError, TimeoutError):
                succ = False
            except Exception as e:
                error_handler(e)
                succ = False

            try:
                acquire_lock()
                if not running:
                    return
                if succ:
                    t.selector.valid(records)
                    succ_num += 1
                progress.update(__task, advance=1)
                if running and progress.finished:
                    history_total = len(t.selector.history.keys())
                    with open(f"{OUTPUT_DIR}/selector_history", "wb") as f:
                        pickle.dump(t.selector.history, f)
                    with open(f"{OUTPUT_DIR}/output", "a") as f:
                        f.write(f"{succ_num / ROUND_SIZE}, {history_total}\n")
                    progress.print(f"Round {round_num+1}: SUCC/ALL = {succ_num}/{ROUND_SIZE}, Explored Grammar Branches = {history_total}")
                    succ_num = 0
                    round_num += 1
                    if round_num == ROUND_NUM:
                        running = False
                        progress.stop()
                    else:
                        progress.reset(__task)
            except KeyboardInterrupt:
                return
            except Exception as e:
                error_handler(e)
            finally:
                lock.locked() and lock.release()

        with BoundThreadPoolExecutor(max_workers=WORKER_NUM) as executor:
            try:
                while running:
                    for _ in range(WORKER_NUM):
                        executor.submit(task)
            except KeyboardInterrupt:
                running = False

        os._exit(0)
