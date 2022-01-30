#!/usr/bin/env python3

from __future__ import annotations

import sys
import enum
import token
import argparse
import tokenize
import itertools
from typing import (
    List,
    Tuple,
    Union,
    TypeVar,
    Iterable,
    Iterator,
    Protocol,
    NamedTuple,
)
from tokenize import TokenInfo

T = TypeVar('T')
U = TypeVar('U')

WHITESPACE_TOKENS = (
    token.NEWLINE,
    token.INDENT,
    token.DEDENT,
    token.NL,
)


class Visitor(Protocol):
    def visitNode(self, node: Node) -> None:
        ...

    def visitSingleTokenNode(self, node: SingleTokenNode) -> None:
        ...

    def visitMultiTokenNode(self, node: MultiTokenNode) -> None:
        ...

    def visitParensGroupNode(self, node: ParensGroupNode) -> None:
        ...


class Error(NamedTuple):
    line: int
    col: int
    message: str


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

    @property
    def start_pos(self) -> Tuple[int, int]:
        return self.children[0].start_pos

    @property
    def start_line(self) -> int:
        return self.start_pos[0]

    @property
    def end_line(self) -> int:
        return self.children[-1].end_line

    def is_single_line(self) -> bool:
        return self.start_line == self.end_line

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

    @property
    def start_pos(self) -> Tuple[int, int]:
        return self.token.start

    @property
    def end_line(self) -> int:
        return self.token.end[0]

    def __repr__(self) -> str:
        return f"SingleTokenNode({self.token!r})"

    def __str__(self) -> str:
        return f"<SingleTokenNode {self.token.string!r}>"


def is_comma(node: Node) -> bool:
    return isinstance(node, SingleTokenNode) and node.kind == NodeKind.COMMA


def is_close_paren(node: Node) -> bool:
    return isinstance(node, SingleTokenNode) and node.kind == NodeKind.CLOSE_PAREN


class MultiTokenNode(Node):
    def __init__(self, tokens: List[TokenInfo]) -> None:
        super().__init__([])
        self.tokens = tokens

    def visit(self, visitor: Visitor) -> None:
        return visitor.visitMultiTokenNode(self)

    @property
    def start_pos(self) -> Tuple[int, int]:
        return self.tokens[0].start

    @property
    def end_line(self) -> int:
        return self.tokens[-1].end[0]

    @property
    def visible_tokens(self) -> List[TokenInfo]:
        return [x for x in self.tokens if x.type not in WHITESPACE_TOKENS]

    def __repr__(self) -> str:
        return f"MultiTokenNode({self.tokens!r})"

    def __str__(self) -> str:
        return f"<MultiTokenNode {' '.join(x.string for x in self.tokens)!r}>"


class ParensGroupNode(Node):
    @staticmethod
    def validate_start_end(start: TokenInfo, end: TokenInfo) -> None:
        expected_end = {
            '(': ')',
            '{': '}',
            '[': ']',
        }[start.string]
        if end.string != expected_end:
            raise ValueError(
                "Start and end must be the same kind of bracket "
                f"(got {start.string!r} and {end.string!r}",
            )

    def __init__(
        self,
        start: SingleTokenNode,
        children: List[Node],
        end: SingleTokenNode,
    ) -> None:
        self.start = start
        self.children = children
        self.end = end

        self.validate_start_end(start.token, end.token)

    def visit(self, visitor: Visitor) -> None:
        return visitor.visitParensGroupNode(self)

    @property
    def start_pos(self) -> Tuple[int, int]:
        return self.start.start_pos

    @property
    def end_line(self) -> int:
        return self.end.end_line

    def iter_comma_separated(self) -> Iterator[Node]:
        yield self.start

        # Split the list of children into chunks using commas as the separator.
        # Use groupby to pick on changes to whether or not the current node is a
        # comma.
        for node_is_comma, children in itertools.groupby(self.children, is_comma):
            if not node_is_comma:
                yield Node(list(children))

        yield self.end

    def __repr__(self) -> str:
        return f"ParensGroupNode({self.start!r}, {self.children!r}, {self.end!r})"

    def __str__(self) -> str:
        children = " ... " if self.children else ""
        return f"<ParensGroupNode {self.start.token.string}{children}{self.end.token.string}>"


class OpenParensGroup:
    def __init__(self, start: SingleTokenNode) -> None:
        self.start = start
        self.children: List[Node] = []

    def complete(self, end: SingleTokenNode) -> ParensGroupNode:
        return ParensGroupNode(self.start, self.children, end)


def parse_ast(tokens: Iterable[TokenInfo]) -> Node:
    stack: List[OpenParensGroup] = []
    spare_tokens: List[TokenInfo] = []
    spare_nodes: List[Node] = []
    root = Node(spare_nodes)

    for tok in tokens:
        if tok.type == token.ENDMARKER or tok.type in WHITESPACE_TOKENS:
            continue

        kind = NodeKind.from_token(tok)

        if kind == NodeKind.OTHER:
            spare_tokens.append(tok)
            continue

        if spare_tokens:
            spare_nodes.append(MultiTokenNode(spare_tokens))
            spare_tokens = []

        if kind == NodeKind.CLOSE_PAREN:
            open_group = stack.pop()
            spare_nodes = stack[-1].children if stack else root.children
            node = open_group.complete(SingleTokenNode(tok))
            spare_nodes.append(node)

        elif kind == NodeKind.OPEN_PAREN:
            open_group = OpenParensGroup(SingleTokenNode(tok))
            stack.append(open_group)
            spare_nodes = open_group.children

        elif kind == NodeKind.COMMA:
            spare_nodes.append(SingleTokenNode(tok))

        else:
            raise AssertionError(f"Unexpected NodeKind {kind!r}")

    if spare_tokens:
        root.children.append(MultiTokenNode(spare_tokens))

    return root


def zip_with_prev(iterable: Iterable[T]) -> Iterable[Tuple[Union[T, U], T]]:
    a, b = itertools.tee(iterable)
    next(b)
    return zip(a, b)


class ValidatingVisitor:
    def __init__(self) -> None:
        self.errors: List[Error] = []
        self._in_multiline_parens_group = False

    def visitChildren(self, node: Node) -> None:
        for child in node.children:
            child.visit(self)

    def visitNode(self, node: Node) -> None:
        self.visitChildren(node)

    def visitSingleTokenNode(self, node: SingleTokenNode) -> None:
        pass

    def visitMultiTokenNode(self, node: MultiTokenNode) -> None:
        pass

    def visitParensGroupNode(self, node: ParensGroupNode) -> None:
        if node.is_single_line() or not node.children:
            return

        # Convert to tuple of (starts on same line as previous, node)
        states = [
            (prev.end_line == cur.start_line, cur)
            for prev, cur in zip_with_prev(node.iter_comma_separated())
        ]

        same_line_starts = [x for same_line_start, x in states if same_line_start]

        if same_line_starts and len(same_line_starts) < len(states):
            self.errors.extend(
                Error(
                    *x.start_pos,
                    f"Closing {x.token.string!r} not wrapped",
                )
                if isinstance(x, SingleTokenNode) and x.kind == NodeKind.CLOSE_PAREN
                else Error(
                    *x.start_pos,
                    "Argument should be wrapped when containing parens are wrapped",
                )
                for x in same_line_starts
            )

        self.visitChildren(node)


def validate(node: Node) -> List[Error]:
    visitor = ValidatingVisitor()
    node.visit(visitor)
    return visitor.errors


def process(tokens: Iterable[TokenInfo]) -> List[Error]:
    return validate(parse_ast(tokens))


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

    for error in errors:
        print(f"{args.file.name}:{error.line}:{error.col}: {error.message}")


def main(argv: List[str] = sys.argv[1:]) -> None:
    return run(parse_args(argv))


if __name__ == '__main__':
    main()
