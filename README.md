# GINGER

<ins>G</ins>inger <ins>I</ins>s <ins>N</ins>ot a <ins>G</ins>AL <ins>E</ins>mulato<ins>R</ins>

![Image](https://raw.githubusercontent.com/and3rson/ginger/main/img/example.jpg)

## So what is this then?

This is a tool that reads GAL `.pld` files and uses `.vec` files to solve equation.
Some may call this an emulator, but it is not: it's just an equation solver that feels like it's "emulating" a real GAL.

## Quick start

```sh
pip install ginger-emulator
ginger ./sample/addr.pld ./sample/addr.vec
```

Please see [sample GAL code](https://github.com/and3rson/ginger/blob/main/sample/addr.pld) and corresponding [vector file](https://github.com/and3rson/ginger/blob/main/sample/addr.vec).

Rules on writing `.vec` files:
- Lines that start with `@` are test case names.

  E.g. `@ Test various stuff`

- Lines that start with `<` list signals that you want to input (each following line needs to set those signals high or low).

  E.g. `< A15 A14 A13 A12 /RD /WR`

- Lines that start with `>` list signals that you want to display after every step.

  E.g. `> /ROM /RAM /IO`

- Lines that start with `?` are test case assertions, they should contain key-value pairs for your tests. Ginger will exit with non-zero code if any test fails.

  E.g. `? /ROM=1 /RAM=0 /IO=1`

- Comments start with `#`. If a comment is added after a vector, it will be printed during run.

- Empty lines are ignored.

- All other non-empty lines are vectors. Whitespaces are ignored and can be added only for visual clarity.

  E.g. `0101 1 1` (equivalent to `0 1 0 1 11` or `010111`)


## Requirements

- Python 3.x
- [Lark parser](https://lark-parser.readthedocs.io/en/stable/)

## Features

Supported:

- Combinatorial logic
- Registered logic
- Tri-states
- Automated test-case assertions
- Arbitrary inversion of signals in inputs/outputs/assertions (e. g. `? /RAM=1` is equivalent to `? RAM=0`)

Not supported (yet?):

- Output enable (ignored)
- Validation of inputs/outputs

Perks:

- Vim syntax highlight file can be found [here](https://github.com/and3rson/ginger/blob/main/vim/syntax/vec.vim).

## Disclaimer & some technical warnings

This tool does not guarantee that the assembled `.pld` code will behave in the same way on a real GAL.
Additionally, it does not guarantee that the `.pld` file is a valid assembly (e. g. it does not validate
if user is trying to use input pins as outputs, term limit, etc, and and will allow the user to do all sorts of silly stuff).

Ginger is using Lark for parsing `.pld` grammar and only validates the **syntax**, not the **semantics**.

So please use, say, `galasm` to assembled the `.pld` file first in order to see if it can be used to program a GAL in the first place,
and then feel free to use Ginger!
