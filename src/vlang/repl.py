"""
Interactive REPL for the vlang compiler.

Usage:
    vlang repl

Multi-line blocks (khi/nếu/hàm) are accumulated until ``hết`` closes them.
Each complete input is JIT-compiled and executed in-process; printf output
appears immediately.
"""

from __future__ import annotations

import sys

_VERSION = "0.1.0"

# Keywords that open a new block scope (first whitespace-delimited token on a line)
_BLOCK_OPEN = frozenset({"khi", "nếu", "neu", "hàm", "ham"})
# Keywords that close a block scope
_BLOCK_CLOSE = frozenset({"hết", "het"})


def _collect_input() -> str | None:
    """Read one complete statement or block from stdin.

    Returns the source text (with trailing newline) or ``None`` on EOF.
    Single-line statements are returned after one Enter; block-opening
    keywords accumulate lines until the matching ``hết`` closes the block.
    """
    lines: list[str] = []
    depth = 0

    while True:
        prompt = "vlang> " if not lines else "  ...> "
        try:
            line = input(prompt)
        except EOFError:
            if lines and any(l.strip() for l in lines):
                return "\n".join(lines) + "\n"
            return None

        # At top level, ignore leading blank lines
        if not line.strip() and depth == 0:
            if lines and any(l.strip() for l in lines):
                break
            continue

        lines.append(line)

        words = line.strip().split()
        if words:
            if words[0] in _BLOCK_OPEN:
                depth += 1
            elif words[0] in _BLOCK_CLOSE:
                depth -= 1

        if depth <= 0:
            break

    if not lines or not any(l.strip() for l in lines):
        return None
    return "\n".join(lines) + "\n"


def _eval_source(source: str) -> None:
    """Compile *source* and JIT-execute it, printing errors to stderr."""
    from vlang.codegen import CodeGen
    from vlang.lexer import Lexer
    from vlang.parser import Parser

    try:
        lexer = Lexer().get_lexer()
        tokens = lexer.lex(source)

        cg = CodeGen()
        pg = Parser()
        pg.parse()
        parser = pg.get_parser()

        ast = parser.parse(tokens)
        cg.generate(ast)
        cg.jit_run()

    except SyntaxError as exc:
        print(f"lỗi cú pháp: {exc}", file=sys.stderr)
    except ValueError as exc:
        print(f"lỗi: {exc}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"lỗi nội bộ: {exc}", file=sys.stderr)


def run_repl() -> None:
    """Start the interactive REPL loop."""
    print(f"vlang REPL v{_VERSION}  —  nhấn Ctrl+C hoặc Ctrl+D để thoát")
    print("Nhập mã vlang (block nhiều dòng kết thúc bằng 'hết'):\n")

    try:
        while True:
            source = _collect_input()
            if source is None:
                print("\nTạm biệt!")
                break
            _eval_source(source)
    except KeyboardInterrupt:
        print("\nTạm biệt!")
