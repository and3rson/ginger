#!/usr/bin/env python3

from argparse import ArgumentParser
from enum import Enum
import re
import sys
from collections import namedtuple
import logging
from typing import Optional
from dataclasses import dataclass

from lark import Lark, Token, Transformer

logging.basicConfig(level=logging.DEBUG)


definition = (
    # fmt: off
    r"""
    %import common.WS_INLINE -> _WS
    %ignore _WS

    start: header "\n"* pins "\n"* equations "\n"* footer

    header: MODEL "\n" NAME "\n"
    MODEL: "GAL16V8" | "GAL20V8" | "GAL22V10"
    NAME: /[A-Za-z0-9_\.]+/

    pins: (PIN+ "\n")+
    PIN: "/"? /[A-Za-z0-9]+/
    MODE: "R" | "T" | "E"
    PIN_EXT: PIN "." MODE

    equations: equation ("\n"+ equation)*
    equation: dest "=" expr
    dest: PIN | PIN_EXT
    expr: addend ("\n"? "+" "\n"? addend)*
    addend: src ("*" src)*
    src: PIN

    footer: "DESCRIPTION" "\n" DESCRIPTION
    DESCRIPTION: (/.*/ "\n")+
    """
    # fmt: on
)

grammar = Lark(definition, debug=True)


@dataclass
class Header:
    model: str
    name: str


@dataclass
class Footer:
    description: str


class PinMode(Enum):
    COMBINATORIAL = "C"
    REGISTERED = "R"
    TRISTRATE = "T"
    ENABLE = "E"


@dataclass
class Pin:
    name: str
    mode: Optional[PinMode] = None
    inv: bool = False

    def __str__(self):
        return f"{'/' if self.inv else ''}{self.name}"

    def __eq__(self, other):
        return self.name == other.name

    def print(self, state):
        value = state[self.name]
        if self.inv:
            value = not value
        return f"{BOLD_GREEN}HIGH    {RESET}" if value else f"{GRAY}LOW     {RESET}"


@dataclass
class Equation:
    pin: Pin
    expr: list[list[Pin]]

    def eval(self, state: dict[str, bool]):
        add_result = False
        for addend in self.expr:
            mul_result = True
            for factor in addend:
                mul_value = state[factor.name]
                if factor.inv:
                    mul_value = not mul_value
                mul_result *= mul_value
            add_result += mul_result
        if self.pin.inv:
            add_result = not add_result
        return add_result


@dataclass
class Tree:
    header: Header
    pins: list[Pin]
    equations: list[Equation]
    footer: Footer


class TreeTransformer(Transformer):
    def header(self, children):
        return Header(model=str(children[0]), name=str(children[1]))

    def footer(self, children):
        return Footer(description=str(children[0]))

    def equations(self, children):
        return children

    def pins(self, children):
        return [
            Pin(
                name=str(child).removeprefix("/"),
                mode=None,
                inv=str(child).startswith("/"),
            )
            for child in children
        ]

    def src(self, children):
        name, _, mode = str(children[0]).partition(".")
        return Pin(
            name=name.removeprefix("/"),
            mode=None,
            inv=name.startswith("/"),
        )

    def dest(self, children):
        name, _, mode = str(children[0]).partition(".")
        return Pin(
            name=name.removeprefix("/"),
            mode=(PinMode(mode.upper()) if mode else PinMode.COMBINATORIAL),
            inv=name.startswith("/"),
        )

    def equation(self, children):
        dest = children[0]
        expr = children[1]
        return Equation(
            pin=dest,
            expr=[[factor for factor in addend.children] for addend in expr.children],
        )

    def start(self, children):
        return Tree(
            header=children[0],
            pins=children[1],
            equations=children[2],
            footer=children[3],
        )


GRAY = "\033[90m"  # ]
RESET = "\033[0m"  # ]
BOLD_GREEN = "\033[1;32m"  # ]


def tick(state, equations: list[Equation]):
    return {equation.pin.name: equation.eval(state) for equation in equations}


def main(source_filename, test_filename):
    with open(sys.argv[1], "r") as fobj:
        content = re.sub(";.*", "", fobj.read())
    tree = grammar.parse(content)
    tree: Tree = TreeTransformer().transform(tree)

    in_pins = []
    out_pins = []
    header_printed = False

    state = {pin.name: False for pin in tree.pins}
    with open(test_filename, "r") as fobj:
        for i, line in enumerate(fobj.readlines()):
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                continue

            if line.startswith("@"):
                # New test
                print("\n" + line.strip("@ ") + "\n")
                header_printed = False
                continue
            if line.startswith("<"):
                in_pins = [
                    Pin(name=x.removeprefix("/"), mode=None, inv=x.startswith("/"))
                    for x in line.strip("< ").split(" ")
                ]
                continue
            if line.startswith(">"):
                out_pins = [
                    Pin(name=x.removeprefix("/"), mode=None, inv=x.startswith("/"))
                    for x in line.strip("> ").split(" ")
                ]
                continue

            line, _, comment = line.partition("#")
            comment = comment.strip()

            line = line.replace(" ", "")
            for ch, pin in zip(line, in_pins):
                if ch == "1":
                    value = True
                elif ch == "0":
                    value = False
                else:
                    continue
                if pin.inv:
                    value = not value
                state[pin.name] = value

            result = {}

            # Execute combinatorial equations
            for equation in tree.equations:
                if equation.pin.mode == PinMode.COMBINATORIAL:
                    result[equation.pin.name] = equation.eval(state)

            # Execute registered equations
            for equation in tree.equations:
                if equation.pin.mode == PinMode.REGISTERED:
                    result[equation.pin.name] = equation.eval(state)

            state.update(result)

            if not header_printed:
                print(
                    "LINE  " + "".join([str(pin).ljust(8) for pin in in_pins]),
                    end="",
                )
                print("|     ", end="")
                print(
                    "".join([str(pin).ljust(8) for pin in out_pins]),
                )
                header_printed = True

            print(str(i + 1).rjust(4) + "  ", end="")
            for pin in in_pins:
                print(pin.print(state), end="")
            print("|     ", end="")
            for pin in out_pins:
                print(pin.print(state), end="")
            print(comment)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "source_filename", help="PLD file to simulate", metavar="SOURCE"
    )
    parser.add_argument("test_filename", help="Test vector file", metavar="TEST")
    args = parser.parse_args()
    main(args.source_filename, args.test_filename)
