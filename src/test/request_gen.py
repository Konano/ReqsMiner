# This file is used to generate a random HTTP request and parse it to check if it is valid

from pathlib import Path

from utils.generator import Tree
from utils.parser import parse

t = Tree(Path("grammar/http.abnf").read_text(), False)
request, _ = t.generate()
print(request)
print(parse(request))
