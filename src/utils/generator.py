"""
Author: Konano
Description: Generator module
"""

import copy
import random
from collections import namedtuple
from math import log, sqrt
from pathlib import Path

import lark

parser = lark.Lark(Path("grammar/abnf.lark").read_text(), parser="lalr", debug=True)


REPEAT_MAX = 100
REPEAT_RAND_COUNT = 3


class Tree:
    class Selector:
        """
        use monte carlo tree search
        """

        class Record:
            # __slots__ = ('used', 'succ')

            def __init__(self, used=0, succ=0) -> None:
                self.used = used
                self.succ = succ

            def use(self) -> None:
                self.used += 1

            def success(self) -> None:
                self.succ += 1

            def __repr__(self) -> str:
                return repr({"used": self.used, "succ": self.succ})

        history = {}  # save all the records of the path, pair of (succ, fail)
        records = []

        def __init__(self, mcts: bool = True) -> None:
            self.mcts = mcts

        def choice(self, path: str, total: int) -> int:
            if total == 1:
                return 0
            """ use UCT alrogithm to choose the next node """
            if not self.mcts:
                self.history[path] = None
                return random.choice(range(total))
            if path in self.history:
                history = self.history[path]
            else:
                history = self.history[path] = [Tree.Selector.Record() for _ in range(total)]
            sum = 0
            for idx, rc in enumerate(history):
                if rc.used == 0:
                    rc.use()
                    self.records.append(rc)
                    return idx
                else:
                    sum += rc.used
            # UCB formula
            weight = [sqrt(2 * log(sum) / rc.used) + rc.succ / rc.used for rc in history]
            # choice = weight.index(max(weight))
            choice = random.choices(range(total), weight)[0]
            history[choice].use()
            self.records.append(history[choice])
            return choice

        def valid(self, records) -> None:
            """when the packet is valid, record success in history"""
            for r in records:
                r.success()

    class Node:
        Limit = namedtuple("Limit", ["min", "max"])

        def __init__(self, name: str, clause: lark.Tree, selector, father: str = None) -> None:
            self.name = name
            self.tree = clause
            self.selector = selector
            self.father = father
            while self.tree.data in ["clause", "brackets_set", "values", "brackets"]:
                self.tree = self.tree.children[0]

        def build(self, nodes: dict) -> None:
            if self.tree.data == "clause_or":
                self.type = "OR"
                self.items = []
                for idx, x in enumerate(self.tree.children):
                    node = Tree.Node(f"O{idx}", x, self.selector, self.name)
                    self.items.append(node)
                    node.build(nodes)
            elif self.tree.data == "clause_and":
                self.type = "AND"
                self.items = []
                for idx, x in enumerate(self.tree.children):
                    node = Tree.Node(f"A{idx}", x, self.selector, self.name)
                    self.items.append(node)
                    node.build(nodes)
            elif self.tree.data == "item":
                token = self.tree.children[0]
                if token.type == "TOKEN":
                    self.type = "NODE"
                    self.value = nodes[token.value]
                elif token.type == "STRING":
                    self.type = "STRING"
                    self.value = eval("b" + token.value)
                else:
                    raise NotImplementedError(self.tree.type)
            elif self.tree.data.startswith("brackets_"):
                self.type = "REPEAT"
                self.limit = self.getLimit()
                node = Tree.Node("R", self.tree.children[-1], self.selector, self.name)
                self.item = node
                node.build(nodes)
            elif self.tree.data.startswith("values_"):
                children = [x.value for x in self.tree.children]
                if "hex" in self.tree.data:
                    values = [int(x + y, 16) for x, y in zip(children[::2], children[1::2])]
                elif "dec" in self.tree.data:
                    values = [int(x) for x in children]
                else:
                    raise NotImplemented(self.tree.data)
                if "range" in self.tree.data:
                    L, R = values
                    self.type = "RANGE"
                    self.items = [bytes(bytearray([x])) for x in range(L, R + 1)]
                else:
                    self.type = "STRING"
                    self.value = bytes(bytearray(values))
            else:
                raise NotImplementedError(self.tree.data)

        def getNumber(self, tree: lark.Tree):
            assert tree.children[0].type == "NUMBER"
            return int(tree.children[0].value)

        def getLimit(self):
            children = self.tree.children
            if self.tree.data == "brackets_01":
                min, max = 0, 1
            if self.tree.data == "brackets_0n":
                min, max = 0, REPEAT_MAX
            if self.tree.data == "brackets_xy":
                min, max = self.getNumber(children[0]), self.getNumber(children[1])
            if self.tree.data == "brackets_xn":
                min, max = self.getNumber(children[0]), REPEAT_MAX
            if self.tree.data == "brackets_0x":
                min, max = 0, self.getNumber(children[0])
            if self.tree.data == "brackets_xx":
                min, max = self.getNumber(children[0]), self.getNumber(children[0])
            return Tree.Node.Limit(min, max)

        def generate(self, path: str) -> bytes:
            path += "." + self.name
            if self.type == "OR":
                return self.items[self.selector.choice(path, len(self.items))].generate(path)
            elif self.type == "AND":
                return b"".join([x.generate(path) for x in self.items])
            elif self.type == "NODE":
                return self.value.generate(path)
            elif self.type == "STRING":
                return self.value
            elif self.type == "RANGE":
                return self.items[self.selector.choice(path, len(self.items))]
            elif self.type == "REPEAT":
                # brackets_xx
                if self.limit.min == self.limit.max:
                    return b"".join([self.item.generate(path) for _ in range(self.limit.min)])
                # brackets_01, brackets_xy, brackets_0x
                if self.limit.max != REPEAT_MAX:
                    total = (
                        self.selector.choice(path, self.limit.max - self.limit.min + 1)
                        + self.limit.min
                    )
                    return b"".join([self.item.generate(path) for _ in range(total)])
                # brackets_0n, brackets_xn
                options = ["RAND"] + [self.limit.min + x for x in range(REPEAT_RAND_COUNT)]
                total = options[self.selector.choice(path, len(options))]
                if isinstance(total, int):
                    return b"".join([self.item.generate(path) for _ in range(total)])
                total = self.limit.min
                while random.randint(0, 1) and total < self.limit.max:
                    total += 1
                return b"".join([self.item.generate(path) for _ in range(total)])
            else:
                raise NotImplementedError(self.type)

    nodes = {}

    def __init__(self, grammar: str, mcts: bool = True) -> None:
        self.selector = self.Selector(mcts)

        tree = parser.parse(grammar)
        for rule in tree.children:
            assert rule.data == "rule"
            name = rule.children[0].value
            clause = rule.children[1].children[0]
            self.nodes[name] = Tree.Node(name, clause, self.selector)

        for name in self.nodes:
            self.nodes[name].build(self.nodes)

    def generate(self, node_name: str = None) -> bytes:
        if node_name is None:
            node_name = "start"
        self.selector.records.clear()
        data = self.nodes[node_name].generate("ROOT")
        return data, copy.copy(self.selector.records)


def check_grammar(filename: str) -> None:
    Tree(Path(filename).read_text(), False)
    print(f'"{filename}" is valid.')


if __name__ == "__main__":
    check_grammar("grammar/http.abnf")
    # print(Tree.Selector.Record().__dict__)
