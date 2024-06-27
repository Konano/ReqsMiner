"""
Author: Konano
Description: Compare the difference between two HTTP requests
"""

import base64
from difflib import SequenceMatcher
from enum import IntEnum

import numpy as np

from utils.parser import parse


class DiffType(IntEnum):
    Retain = 0
    Modify = 1
    Add = 2
    Del = 3
    DupAdd = 4
    DupDel = 5
    ReduceRows = 6


DiffTypeName = list(DiffType.__members__.keys())


class Diff(object):
    def __init__(self, type, field, before=None, after=None, token="", host="", unique=True) -> None:
        self.type = type
        self.field = field
        self.before = before
        self.after = after
        self.token = token
        self.host = host
        self.unique = unique
        self.label = {
            DiffType.Retain: "=",
            DiffType.Modify: "*",
            DiffType.Add: "+",
            DiffType.Del: "-",
            DiffType.DupAdd: "++",
            DiffType.DupDel: "--",
            DiffType.ReduceRows: "%",
        }
        self.color = {
            DiffType.Modify: "\033[0;33m",  # YELLOW
            DiffType.Add: "\033[0;36m",  # CYAN
            DiffType.Del: "\033[0;31m",  # RED
            DiffType.DupAdd: "\033[0;36m",  # CYAN
            DiffType.DupDel: "\033[0;31m",  # RED
            DiffType.ReduceRows: "\033[0;33m",  # YELLOW
        }

    # def __repr__(self) -> str:
    #     return f'{self.label[self.type]}: {self.field}\n\t{self.before}\n\t{self.after}'

    def __str__(self) -> str:
        if self.type in [DiffType.Retain]:
            return (
                f"{self.label[self.type]}: {self.field} {self.token} {self.host}\n\t{self.before}"
            )
        if self.type in [DiffType.Del, DiffType.DupDel]:
            return (
                f"{self.color[self.type]}{self.label[self.type]}: {self.field} {self.token} {self.host}\n\t{self.before}"
                + "\033[0m"
            )
        if self.type in [DiffType.Add, DiffType.DupAdd]:
            return (
                f"{self.color[self.type]}{self.label[self.type]}: {self.field} {self.token} {self.host}\n\t{self.after}"
                + "\033[0m"
            )
        if self.type in [DiffType.Modify, DiffType.ReduceRows]:
            return (
                f"{self.color[self.type]}{self.label[self.type]}: {self.field} {self.token} {self.host}\n\t{self.before}\n\t{self.after}"
                + "\033[0m"
            )
        return f"?: {self.field} {self.token} {self.host}\n\t{self.before}\n\t{self.after}"

    def __hash__(self) -> int:
        return self.type + hash(self.field) + hash(self.before) + hash(self.after) + hash(self.host)

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, self.__class__):
            if self.unique:
                return self.__hash__() == __o.__hash__()
            return self.__dict__ == __o.__dict__
        else:
            return False

    def __repr__(self) -> str:
        return repr([int(self.type), self.field, self.before, self.after])

    def dump_mongodb(self, token, host):
        return {
            "token": token,
            "host": host,
            "type": int(self.type),
            "field": self.field,
            "before": self.before,
            "after": self.after,
        }


def diff_analy(A, B):
    A = parse(A)
    B = parse(B)

    if A is None or B is None:
        return []

    diffs = []
    for key in ["method", "url", "http_version", "message_body"]:
        if A[key] == B[key]:
            diffs.append(Diff(DiffType.Retain, key, A[key], B[key]))
        elif not len(A[key]) and len(B[key]):
            diffs.append(Diff(DiffType.Add, key, A[key], B[key]))
        elif len(A[key]) and not len(B[key]):
            diffs.append(Diff(DiffType.Del, key, A[key], B[key]))
        else:
            diffs.append(Diff(DiffType.Modify, key, A[key], B[key]))

    A_headers = sorted(A["headers"])
    B_headers = sorted(B["headers"])

    matcher = SequenceMatcher()

    # deal with multiple same HTTP Headers
    An, Bn = 0, 0
    while An < len(A_headers) and Bn < len(B_headers):
        if A_headers[An][0] < B_headers[Bn][0]:
            header_name = A_headers[An][0].decode("utf8")
            diffs.append(Diff(DiffType.Del, f"{header_name}", before=A_headers[An][1]))
            An += 1
        elif A_headers[An][0] > B_headers[Bn][0]:
            header_name = B_headers[Bn][0].decode("utf8")
            diffs.append(Diff(DiffType.Add, f"{header_name}", after=B_headers[Bn][1]))
            Bn += 1
        else:
            header_name = A_headers[An][0].decode("utf8")
            Am, Bm = 1, 1
            while An + Am < len(A_headers) and A_headers[An][0] == A_headers[An + Am][0]:
                Am += 1
            while Bn + Bm < len(B_headers) and B_headers[Bn][0] == B_headers[Bn + Bm][0]:
                Bm += 1
            ratio = np.zeros((Am, Bm), dtype=float)
            Ax = set(range(Am))
            Bx = set(range(Bm))
            for i in range(Am):
                matcher.set_seq1(A_headers[An + i][1])
                for j in range(Bm):
                    if A_headers[An + i][1] == B_headers[Bn + j][1]:
                        ratio[i, j] = 1
                    else:
                        matcher.set_seq2(B_headers[Bn + j][1])
                        ratio[i, j] = matcher.ratio()
            while np.max(ratio) != -1:
                i, j = np.unravel_index(ratio.argmax(), ratio.shape)
                ratio[i, :] = ratio[:, j] = -1
                Ax.remove(i)
                Bx.remove(j)
                before = A_headers[An + i][1]
                after = B_headers[Bn + j][1]
                if before == after:
                    diffs.append(Diff(DiffType.Retain, f"{header_name}", before=before))
                elif before.split(b"\r\n")[0] == after:
                    diffs.append(Diff(DiffType.ReduceRows, f"{header_name}", before, after))
                else:
                    diffs.append(Diff(DiffType.Modify, f"{header_name}", before, after))

            for x in Ax:
                diffs.append(Diff(DiffType.DupDel, f"{header_name}", before=A_headers[An + x][1]))
            for x in Bx:
                diffs.append(Diff(DiffType.DupAdd, f"{header_name}", after=B_headers[Bn + x][1]))
            An += Am
            Bn += Bm

    return diffs


if __name__ == "__main__":
    packet = base64.b64decode(
        "Q09QWSAvNWQ3NWU3ODQ3ZDY2ZWU5Mi40IEhUVFAvMC45DQpBcHBseS1Uby1SZWRpcmVjdC1SZWY6DQpIb3N0OiAJIHZlcml6b24ubmlzbC5hYwkJDQpEYXRlOiAgCQkJDQpQdWJsaWMtS2V5LVBpbnMtUmVwb3J0LU9ubHk6CQ0KT0RhdGEtVmVyc2lvbjo0LjAgIA0KRGlnZXN0OgkNCkNvbnRlbnQtRW5jb2Rpbmc6LAkJLAksCQksIAlkZWZsYXRlCQksLSAJDQpDbG9zZTogIAkJDQoNCg=="
    )
    through = base64.b64decode(
        "Q09QWSAvNWQ3NWU3ODQ3ZDY2ZWU5Mi40IEhUVFAvMS4wDQpBcHBseS1Uby1SZWRpcmVjdC1SZWY6IA0KSG9zdDogdmVyaXpvbi5uaXNsLmFjCQkNCkRhdGU6IA0KUHVibGljLUtleS1QaW5zLVJlcG9ydC1Pbmx5OiANCk9EYXRhLVZlcnNpb246IDQuMCAgDQpEaWdlc3Q6IA0KQ29udGVudC1FbmNvZGluZzogLAkJLAksCQksIAlkZWZsYXRlCQksLSAJDQpDbG9zZTogSAnUICog/jMyNTYyMGQyYmY5NjczYzQgDQpYLUVDLVV1aWQ6IDExNjgyMTk5MjA3NTM5MzE2NTY0MTAyMDg1ODUwMDU1MzYwMjEwNDQNClgtRUMtU2Vzc2lvbi1JRDogMTE2ODIxOTkyMDc1MzkzMTY1NjQxMDIwODU4NTAwNTUzNjAyMTA0NA0KeC1lYy1wb3A6IHNnZA0KWC1Gb3J3YXJkZWQtRm9yOiAyMDIuMTEyLjUxLjc4DQpYLUhvc3Q6IHZlcml6b24ubmlzbC5hYwkJDQpYLUZvcndhcmRlZC1Qcm90bzogaHR0cA0KVmlhOiBIVFRQLzEuMCBFQ0FjYyAoc2dkL0YwQUUpDQpDb25uZWN0aW9uOiBrZWVwLWFsaXZlDQoNCg=="
    )

    records = diff_analy(packet, through)

    # __str__
    for x in records:
        print(str(x))

    # __repr__
    print(records)
