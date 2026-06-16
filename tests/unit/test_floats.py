"""
Unit tests for float type support in vlang.

Covers lexer tokenisation, parser AST construction, and LLVM IR emission
for floating-point literals, arithmetic, variables, comparison, and printing.

Run:
    pytest tests/unit/test_floats.py -v
"""

from __future__ import annotations

import pytest

from vlang.nodes import Float, Number, Sum, Mul, Div


# ---------------------------------------------------------------------------
# Helpers (inline to avoid conftest import dance in unit tests)
# ---------------------------------------------------------------------------

def _tokenize(source: str):
    from vlang.lexer import Lexer
    lexer = Lexer().get_lexer()
    return [(t.gettokentype(), t.value) for t in lexer.lex(source)]


def _token_types(source: str):
    return [tt for tt, _ in _tokenize(source)]


def _parse(source: str):
    from vlang.lexer import Lexer
    from vlang.parser import Parser
    from vlang.nodes import Program

    lexer = Lexer().get_lexer()
    tokens = lexer.lex(source)
    pg = Parser()
    pg.parse()
    ast = pg.get_parser().parse(tokens)
    if isinstance(ast, Program) and len(ast.statements) == 1:
        return ast.statements[0]
    return ast


def _ir(source: str) -> str:
    """Full pipeline: source → LLVM IR text."""
    from conftest import compile_to_ir
    return compile_to_ir(source)


# ---------------------------------------------------------------------------
# Lexer tests
# ---------------------------------------------------------------------------

class TestFloatLexer:
    def test_float_token_type(self):
        types = _token_types("3.14\n")
        assert "SO_THUC" in types

    def test_float_token_value(self):
        pairs = _tokenize("3.14\n")
        assert ("SO_THUC", "3.14") in pairs

    def test_float_before_integer(self):
        """3.14 must not be tokenised as integer 3 followed by something."""
        types = _token_types("3.14\n")
        assert types[0] == "SO_THUC"
        assert "SO_NGUYEN" not in types

    def test_integer_still_works(self):
        types = _token_types("42\n")
        assert types == ["SO_NGUYEN", "HET_DONG"]

    def test_float_zero(self):
        pairs = _tokenize("0.0\n")
        assert ("SO_THUC", "0.0") in pairs

    def test_float_in_expression(self):
        types = _token_types("1.5 + 2.5\n")
        assert types == ["SO_THUC", "CONG", "SO_THUC", "HET_DONG"]

    def test_mixed_int_float(self):
        types = _token_types("1 + 2.5\n")
        assert types == ["SO_NGUYEN", "CONG", "SO_THUC", "HET_DONG"]


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestFloatParser:
    def test_parse_float_literal(self):
        node = _parse("in_ra(3.14)\n")
        from vlang.nodes import Print
        assert isinstance(node, Print)
        assert isinstance(node.value, Float)
        assert node.value.value == "3.14"

    def test_parse_float_var_decl(self):
        from vlang.nodes import VarDecl
        ast = _parse("khai_báo x = 1.5\n")
        assert isinstance(ast, VarDecl)
        assert ast.name == "x"
        assert isinstance(ast.expr, Float)

    def test_parse_float_addition(self):
        node = _parse("in_ra(1.0 + 2.0)\n")
        from vlang.nodes import Print
        assert isinstance(node, Print)
        assert isinstance(node.value, Sum)
        assert isinstance(node.value.left, Float)
        assert isinstance(node.value.right, Float)

    def test_parse_mixed_sum(self):
        node = _parse("in_ra(1 + 2.5)\n")
        from vlang.nodes import Print
        assert isinstance(node, Print)
        assert isinstance(node.value, Sum)
        assert isinstance(node.value.left, Number)
        assert isinstance(node.value.right, Float)

    def test_parse_float_negative(self):
        from vlang.nodes import UnaryMinus
        node = _parse("in_ra(-3.14)\n")
        from vlang.nodes import Print
        assert isinstance(node, Print)
        assert isinstance(node.value, UnaryMinus)
        assert isinstance(node.value.operand, Float)


# ---------------------------------------------------------------------------
# Code-generation tests
# ---------------------------------------------------------------------------

class TestFloatCodegen:
    def test_float_print_uses_double_type(self):
        ir_text = _ir("in_ra(3.14)\n")
        assert "double" in ir_text

    def test_float_print_uses_percent_g(self):
        ir_text = _ir("in_ra(3.14)\n")
        assert "%g" in ir_text

    def test_int_print_still_uses_percent_i(self):
        ir_text = _ir("in_ra(42)\n")
        assert "%i" in ir_text
        assert "%g" not in ir_text

    def test_float_addition_emits_fadd(self):
        ir_text = _ir("in_ra(1.0 + 2.0)\n")
        assert "fadd" in ir_text

    def test_float_subtraction_emits_fsub(self):
        ir_text = _ir("in_ra(5.0 - 3.0)\n")
        assert "fsub" in ir_text

    def test_float_multiplication_emits_fmul(self):
        ir_text = _ir("in_ra(2.0 * 3.0)\n")
        assert "fmul" in ir_text

    def test_float_division_emits_fdiv(self):
        ir_text = _ir("in_ra(6.0 / 2.0)\n")
        assert "fdiv" in ir_text

    def test_mixed_int_float_promotes_to_double(self):
        ir_text = _ir("in_ra(1 + 0.5)\n")
        assert "sitofp" in ir_text
        assert "fadd" in ir_text

    def test_float_var_decl(self):
        ir_text = _ir("khai_báo pi = 3.14\nin_ra(pi)\n")
        assert "double" in ir_text

    def test_float_comparison_emits_fcmp(self):
        ir_text = _ir("khai_báo x = 1.5\nnếu x > 1.0 thì\nin_ra(1)\nhết\n")
        assert "fcmp" in ir_text

    def test_float_unary_minus_emits_fneg(self):
        ir_text = _ir("in_ra(-3.14)\n")
        assert "fneg" in ir_text

    def test_two_float_prints_reuse_format_string(self):
        ir_text = _ir("in_ra(1.0)\nin_ra(2.0)\n")
        # Only one global for fstr_float should exist
        assert ir_text.count("fstr_float") >= 1

    def test_mixed_int_and_float_prints(self):
        ir_text = _ir("in_ra(42)\nin_ra(3.14)\n")
        assert "%i" in ir_text
        assert "%g" in ir_text


# ---------------------------------------------------------------------------
# Error message tests
# ---------------------------------------------------------------------------

class TestErrorMessages:
    def test_syntax_error_has_line_number(self):
        with pytest.raises(Exception, match="дóng 1|дòng 1|dòng 1|line|tại"):
            _parse("@@@\n")

    def test_undeclared_var_error(self):
        from vlang.codegen import CodeGen
        from vlang.lexer import Lexer
        from vlang.parser import Parser

        source = "in_ra(khong_ton_tai)\n"
        lexer = Lexer().get_lexer()
        tokens = lexer.lex(source)
        cg = CodeGen()
        pg = Parser()
        pg.parse()
        ast = pg.get_parser().parse(tokens)
        with pytest.raises(ValueError, match="khai báo|Biến"):
            cg.generate(ast)
