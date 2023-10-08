# ginger

Ginger Is Not a GAL EmulatoR

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
- Lines that start with `<` list signals that you want to input (and each following line needs to set those signals high or low).
- Lines that start with `>` list signals that you want to display after every step.
- Comments start with `#`. If a comment is added after a vector, it will be printed during run.
- Empty lines are ignored.
- All other lines are vectors.


## Requirements

- Python 3.x
- [Lark parser](https://lark-parser.readthedocs.io/en/stable/)

## Features

Supported:

- Combinatorial logic
- Registered logic

Not supported (yet?):

- Tri-states
- Output enable (ignored)
- Validation of inputs/outputs
- Automated test-case assertions

## Disclaimer & some technical warnings

This tool does not guarantee that the assembled `.pld` code will behave in the same way on a real GAL.
Additionally, it does not guarantee that the `.pld` file is a valid assembly (e. g. it does not validate
if user is trying to use input pins as outputs, term limit, etc, and and will allow the user to do all sorts of silly stuff).

Ginger is using Lark for parsing `.pld` grammar and only validates the **syntax**, not the **semantics**.

So please use, say, `galasm` to assembled the `.pld` file first in order to see if it can be used to program a GAL in the first place,
and then feel free to use Ginger!
