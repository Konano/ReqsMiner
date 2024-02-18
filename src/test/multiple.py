"""
Author: Konano
Description: Just for test
"""

import sys
from pathlib import Path

from rich.progress import track

from utils.generator import Tree
from utils.log import error_handler, logger
from utils.parser import parse

t = Tree(Path("grammar/http.abnf").read_text(), False)


# generate request randomly then parse
def test():
    try:
        for _ in track(range(100000)):
            request, _ = t.generate()
            assert parse(request)
        logger.info("Test passed!")
    except Exception as e:
        logger.error("Test failed!")
        error_handler(e)


if __name__ == "__main__":
    test()
