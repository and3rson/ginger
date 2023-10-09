#!/usr/bin/env python3

from argparse import ArgumentParser
from enum import Enum
import re
import sys
from collections import namedtuple
import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

from lark import Lark, Token, Transformer

logging.basicConfig(level=logging.DEBUG)


definition = (
    # fmt: off
    r'''
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
    '''
    # fmt: on
)

grammar = Lark(definition, debug=True)

GRAY = '\033[90m'  # ]
RESET = '\033[0m'  # ]
BOLD_GREEN = '\033[1;32m'  # ]
BLUE = '\033[34m'  # ]
BOLD_RED = '\033[1;31m'  # ]


class PinMode(Enum):
    COMBINATORIAL = 'C'
    REGISTERED = 'R'
    TRISTATE = 'T'
    ENABLE = 'E'


@dataclass
class Header:
    model: str
    name: str


@dataclass
class Footer:
    description: str


@dataclass(frozen=True)
class Pin:
    name: str
    mode: Optional[PinMode] = None
    inv: bool = False

    @classmethod
    def from_str(cls, s: str, mode=None) -> 'Pin':
        return Pin(name=s.removeprefix('/'), mode=mode, inv=s.startswith('/'))

    def __str__(self):
        return ('/' if self.inv else '') + self.name

    def __eq__(self, other):
        return self.name == other.name

    def value(self, state) -> Optional[bool]:
        value = state[self.name]
        if value is not None:
            if self.inv:
                value = not value
        return value


@dataclass(frozen=True)
class Equation:
    pin: Pin
    expr: Tuple[Tuple[Pin]]

    @property
    def dependencies(self) -> List[Pin]:
        return [factor for addend in self.expr for factor in addend]

    def eval(self, state: Dict[str, bool]):
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
        return bool(add_result)


@dataclass
class Tree:
    header: Header
    pins: List[Pin]
    equations: List[Equation]
    footer: Footer


class TreeTransformer(Transformer):
    def header(self, children):
        return Header(model=str(children[0]), name=str(children[1]))

    def footer(self, children):
        return Footer(description=str(children[0]))

    def equations(self, children):
        def iter_tree(equation):
            if equation.pin.mode == PinMode.REGISTERED:
                return
            for pin in equation.dependencies:
                needed_equation = next((x for x in children if x.pin == pin and x.pin != equation.pin), None)
                if needed_equation:
                    yield from iter_tree(needed_equation)
            yield equation

        seen = set()
        result = []
        for root_equation in children:
            for equation in iter_tree(root_equation):
                if equation not in seen:
                    seen.add(equation)
                    result.append(equation)

        for equation in children:
            if equation.pin.mode == PinMode.REGISTERED:
                result.append(equation)

        return result

    def pins(self, children):
        return [Pin.from_str(str(child)) for child in children]

    def src(self, children):
        name, _, mode = str(children[0]).partition('.')
        return Pin.from_str(name)

    def dest(self, children):
        name, _, mode = str(children[0]).partition('.')
        return Pin.from_str(name, PinMode(mode.upper()) if mode else PinMode.COMBINATORIAL)

    def equation(self, children):
        dest = children[0]
        expr = children[1]
        return Equation(
            pin=dest,
            expr=tuple([tuple([factor for factor in addend.children]) for addend in expr.children]),
        )

    def start(self, children):
        return Tree(
            header=children[0],
            pins=children[1],
            equations=children[2],
            footer=children[3],
        )


def pretty_value(value, ljust=0):
    color = {True: BOLD_GREEN, False: GRAY, None: BLUE}[value]
    label = {True: 'HIGH', False: 'LOW', None: 'Z'}[value]
    return f'{color}{label.ljust(ljust)}{RESET}'


def main(source_filename, test_filename):
    with open(sys.argv[1], 'r') as fobj:
        content = re.sub(';.*', '', fobj.read())
    tree = grammar.parse(content)
    tree: Tree = TreeTransformer().transform(tree)

    in_pins = []
    out_pins = []
    header_printed = False
    failures = 0

    state = {pin.name: False for pin in tree.pins}
    with open(test_filename, 'r') as fobj:
        for i, line in enumerate(fobj.readlines()):
            line = line.strip()
            if not line:
                continue
            if line.startswith('#'):
                continue

            if line.startswith('@'):
                # New test
                print('\n' + line.strip('@ ') + '\n')
                header_printed = False
                continue
            if line.startswith('<'):
                in_pins = [Pin.from_str(x) for x in line.strip('< ').split(' ')]
                continue
            if line.startswith('>'):
                out_pins = [Pin.from_str(x) for x in line.strip('> ').split(' ')]
                continue
            if line.startswith('?'):
                # Test case
                line = line.strip('? ')
                test_ok = True
                for name, value in [term.strip().split('=') for term in line.split(' ')]:
                    expected = True if value == '1' else False if value == '0' else None
                    actual = Pin.from_str(name).value(state)
                    if expected != actual:
                        print(
                            f'{str(i+1).rjust(4)}  {BOLD_RED}ERROR{RESET}: {name} expected {pretty_value(expected)} but got {pretty_value(actual)}'
                        )
                        test_ok = False
                if not test_ok:
                    failures += 1
                continue

            line, _, comment = line.partition('#')
            comment = comment.strip()

            line = line.replace(' ', '')
            for ch, pin in zip(line, in_pins):
                if ch == '1':
                    value = True
                elif ch == '0':
                    value = False
                else:
                    continue
                if pin.inv:
                    value = not value
                state[pin.name] = value

            result = {}
            tristates = {}

            # Execute combinatorial equations
            for equation in tree.equations:
                if equation.pin.mode in (PinMode.COMBINATORIAL, PinMode.TRISTATE):
                    state[equation.pin.name] = equation.eval(state)
                elif equation.pin.mode == PinMode.ENABLE:
                    tristates[equation.pin.name] = equation.eval(state)
            # Execute registered equations
            for equation in tree.equations:
                if equation.pin.mode == PinMode.REGISTERED:
                    result[equation.pin.name] = equation.eval(state)

            state.update(result)
            state.update({pin: None for pin, value in tristates.items() if not value})

            if not header_printed:
                print(
                    'LINE  ' + ''.join([str(pin).ljust(8) for pin in in_pins]),
                    end='',
                )
                print('|     ', end='')
                print(
                    ''.join([str(pin).ljust(8) for pin in out_pins]),
                )
                header_printed = True

            print(str(i + 1).rjust(4) + '  ', end='')
            for pin in in_pins:
                print(pretty_value(pin.value(state), 8), end='')
            print('|     ', end='')
            for pin in out_pins:
                print(pretty_value(pin.value(state), 8), end='')
            print(comment)

    if failures > 0:
        print()
        print(f'{BOLD_RED}{failures} test(s) failed{RESET}.')
        return 1

    return 0


def cli():
    parser = ArgumentParser()
    parser.add_argument('source_filename', help='PLD file to simulate', metavar='SOURCE')
    parser.add_argument('test_filename', help='Test vector file', metavar='TEST')
    args = parser.parse_args()
    sys.exit(main(args.source_filename, args.test_filename))


if __name__ == '__main__':
    cli()
