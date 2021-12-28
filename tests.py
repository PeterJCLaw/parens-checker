#!/usr/bin/env python3

import io
import textwrap
import tokenize
import unittest
import contextlib
from typing import List, Iterator

import checker
from checker import Node, MultiTokenNode, SingleTokenNode


class StringifyVisitor:
    def __init__(self) -> None:
        self.parts: List[str] = []
        self._prefix = ""
        self._indent = ""
        self._suffix = ""

    def to_string(self) -> str:
        return "".join(self.parts)

    @contextlib.contextmanager
    def prefix(self, prefix: str) -> Iterator[None]:
        original, self._prefix = self._prefix, prefix
        try:
            yield
        finally:
            self._prefix = original

    @contextlib.contextmanager
    def indent(self) -> Iterator[None]:
        self._indent += "  "
        try:
            yield
        finally:
            self._indent = self._indent[:-2]

    @contextlib.contextmanager
    def suffix(self, suffix: str) -> Iterator[None]:
        original, self._suffix = self._suffix, suffix
        try:
            yield
        finally:
            self._suffix = original

    def visitChildren(self, node: Node) -> None:
        for child in node.children:
            child.visit(self)

    def appendPart(self, string: str) -> None:
        self.parts.append(self._indent)
        self.parts.append(self._prefix)
        self.parts.append(string)
        self.parts.append(self._suffix)

    def visitNode(self, node: Node) -> None:
        with self.suffix("\n"):
            name = type(node).__name__
            if node.children:
                self.appendPart(f'{name}:')

                indent = self.indent() if self._prefix else contextlib.nullcontext()
                with indent, self.prefix("- "):
                    self.visitChildren(node)
            else:
                self.appendPart(f'{name}: []')

    def visitSingleTokenNode(self, node: SingleTokenNode) -> None:
        self.appendPart(str(node))

    def visitMultiTokenNode(self, node: MultiTokenNode) -> None:
        self.appendPart(str(node))


class TestAST(unittest.TestCase):
    def assertAst(self, text: str, expected: str) -> None:
        text = textwrap.dedent(text.lstrip('\n'))
        expected = textwrap.dedent(expected.lstrip('\n'))

        ast = checker.parse_ast(
            tokenize.generate_tokens(
                io.StringIO(text).readline,
            ),
        )

        visitor = StringifyVisitor()
        ast.visit(visitor)
        actual = visitor.to_string()

        self.assertEqual(expected, actual)

    def test_no_call(self) -> None:
        self.assertAst(
            'foo',
            '''
            Node:
            - <MultiTokenNode 'foo  '>
            ''',
        )

    def test_call(self) -> None:
        self.assertAst(
            'foo()',
            r'''
            Node:
            - <MultiTokenNode 'foo'>
            - <SingleTokenNode '('>
            - Node: []
            - <SingleTokenNode ')'>
            - <MultiTokenNode ' '>
            ''',
        )

    def test_nested_call(self) -> None:
        self.assertAst(
            'foo(bar())',
            r'''
            Node:
            - <MultiTokenNode 'foo'>
            - <SingleTokenNode '('>
            - Node:
              - <MultiTokenNode 'bar'>
              - <SingleTokenNode '('>
              - Node: []
              - <SingleTokenNode ')'>
            - <SingleTokenNode ')'>
            - <MultiTokenNode ' '>
            ''',
        )

    def test_definition(self) -> None:
        self.assertAst(
            '''
            def foo():
                ...
            ''',
            r'''
            Node:
            - <MultiTokenNode 'def foo'>
            - <SingleTokenNode '('>
            - Node: []
            - <SingleTokenNode ')'>
            - <MultiTokenNode ': \n      ... \n  '>
            ''',
        )


if __name__ == '__main__':
    unittest.main()
