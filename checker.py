#!/usr/bin/env python3

from __future__ import annotations

import sys
import enum
import token
import argparse
import tokenize
from typing import List, Iterable, Protocol
from tokenize import TokenInfo


class Visitor(Protocol):
    def visitNode(self, node: Node) -> None:
        ...

    def visitSingleTokenNode(self, node: SingleTokenNode) -> None:
        ...

    def visitMultiTokenNode(self, node: MultiTokenNode) -> None:
        ...


class Error:
    ...


class NodeKind(enum.Enum):
    COMMA = 'comma'
    OPEN_PAREN = 'open_paren'
    CLOSE_PAREN = 'close_paren'
    OTHER = 'other'

    @classmethod
    def from_token(cls, tok: TokenInfo) -> NodeKind:
        if tok.type == token.OP:
            if tok.string == ',':
                return cls.COMMA

            if tok.string in '([{':
                return cls.OPEN_PAREN

            if tok.string in ')]}':
                return cls.CLOSE_PAREN

        return cls.OTHER


class Node:
    def __init__(self, children: List[Node]) -> None:
        self.children: List[Node] = children

    def visit(self, visitor: Visitor) -> None:
        return visitor.visitNode(self)

    def __repr__(self) -> str:
        return f"Node({self.children!r})"


class SingleTokenNode(Node):
    def __init__(self, tok: TokenInfo) -> None:
        super().__init__([])
        self.token = tok
        self.kind = NodeKind.from_token(tok)
        if self.kind is NodeKind.OTHER:
            raise ValueError(f"Unexpected token kind {tok!r} for single token node")

    def visit(self, visitor: Visitor) -> None:
        return visitor.visitSingleTokenNode(self)

    def __repr__(self) -> str:
        return f"SingleTokenNode({self.token!r})"

    def __str__(self) -> str:
        return f"<SingleTokenNode {self.token.string!r}>"


class MultiTokenNode(Node):
    def __init__(self, tokens: List[TokenInfo]) -> None:
        super().__init__([])
        self.tokens = tokens

    def visit(self, visitor: Visitor) -> None:
        return visitor.visitMultiTokenNode(self)

    def __repr__(self) -> str:
        return f"MultiTokenNode({self.tokens!r})"

    def __str__(self) -> str:
        return f"<MultiTokenNode {' '.join(x.string for x in self.tokens)!r}>"


def parse_ast(tokens: Iterable[TokenInfo]) -> Node:
    parent = Node([])
    stack: List[Node] = []
    spare_tokens: List[TokenInfo] = []

    for tok in tokens:
        kind = NodeKind.from_token(tok)

        if kind == NodeKind.OTHER:
            spare_tokens.append(tok)
            continue

        if spare_tokens:
            parent.children.append(MultiTokenNode(spare_tokens))
            spare_tokens = []

        if kind == NodeKind.CLOSE_PAREN:
            parent = stack.pop()

        node = SingleTokenNode(tok)
        parent.children.append(node)

        if kind == NodeKind.OPEN_PAREN:
            new_parent = Node([])
            parent.children.append(new_parent)
            stack.append(parent)
            parent = new_parent
            del new_parent

    if spare_tokens:
        parent.children.append(MultiTokenNode(spare_tokens))

    return parent


def process(tokens: Iterable[TokenInfo]) -> List[Error]:
    return []


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'file',
        type=argparse.FileType(mode='rt'),
        help="The file to read from. Use '-' to read from STDIN.",
    )
    return parser.parse_args()


def run(args: argparse.Namespace) -> None:
    with args.file:
        token_stream = tokenize.generate_tokens(args.file.readline)

    errors = process(token_stream)
    print(errors)


def main(argv: List[str] = sys.argv[1:]) -> None:
    return run(parse_args(argv))


if __name__ == '__main__':
    main()
