"""
AST node classes for the vlang compiler.

Each node represents a syntactic construct in the .vpl source language.
Nodes are **pure data**: they hold only structural fields and carry no
dependency on LLVM. All LLVM IR emission lives in
``vlang.visitor.CodeGenVisitor``, which walks these nodes.

Named ``nodes`` (not ``ast``) to avoid shadowing Python's stdlib ``ast`` module.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Primitive nodes
# ---------------------------------------------------------------------------

@dataclass
class Number:
    """An integer literal node. ``value`` is the raw source string."""

    value: str


@dataclass
class Float:
    """A floating-point literal node. ``value`` is the raw source string."""

    value: str


@dataclass
class Boolean:
    """A boolean literal node (``đúng`` / ``sai``)."""

    value: bool


# ---------------------------------------------------------------------------
# Binary operator base class
# ---------------------------------------------------------------------------

@dataclass
class BinaryOp:
    """Base class for binary operations holding ``left`` and ``right`` operands."""

    left: object
    right: object


class Sum(BinaryOp):
    """Addition: left + right  (cộng)."""


class Sub(BinaryOp):
    """Subtraction: left - right  (trừ)."""


class Mul(BinaryOp):
    """Multiplication: left * right  (nhân)."""


class Div(BinaryOp):
    """Signed integer division: left / right  (chia)."""


class Mod(BinaryOp):
    """Signed integer remainder: left % right (chia lấy dư)."""


class LogicalAnd(BinaryOp):
    """Logical AND: left && right  (và)."""


class LogicalOr(BinaryOp):
    """Logical OR: left || right  (hoặc)."""


# ---------------------------------------------------------------------------
# Statement nodes
# ---------------------------------------------------------------------------

@dataclass
class Print:
    """Print statement node: in_ra(expression)."""

    value: object


@dataclass
class Program:
    """A collection of statements representing a complete program."""

    statements: list = field(default_factory=list)

    def add_statement(self, statement) -> None:
        self.statements.append(statement)


@dataclass
class EmptyStatement:
    """An empty statement (e.g. newline or comment)."""


# ---------------------------------------------------------------------------
# Variable nodes
# ---------------------------------------------------------------------------

@dataclass
class VarDecl:
    """Variable declaration node: khai_báo name = expr."""

    name: str
    expr: object


@dataclass
class VarAssign:
    """Variable assignment node: name = expr."""

    name: str
    expr: object


@dataclass
class VarRef:
    """Variable reference node: name."""

    name: str


# ---------------------------------------------------------------------------
# Comparison node
# ---------------------------------------------------------------------------

@dataclass
class Compare:
    """Comparison operator node: left op right.

    ``op_token`` is the raw token-type string (e.g. ``"NHO_HON"``); the
    visitor maps it to an LLVM comparison predicate.
    """

    left: object
    op_token: str
    right: object


# ---------------------------------------------------------------------------
# Loop / conditional nodes
# ---------------------------------------------------------------------------

@dataclass
class WhileLoop:
    """While loop node: khi condition thì ... hết."""

    condition: object
    body: object


@dataclass
class IfStmt:
    """If statement node: nếu condition thì ... [khác_thì ...] hết."""

    condition: object
    then_body: object
    else_body: object = None


# ---------------------------------------------------------------------------
# Function nodes
# ---------------------------------------------------------------------------

@dataclass
class FuncDef:
    """Function definition node: hàm name(params) ... hết."""

    name: str
    params: list
    body: object


@dataclass
class ReturnStmt:
    """Return statement node: trả_về expr."""

    expr: object


@dataclass
class CallExpr:
    """Call expression node: name(args)."""

    name: str
    args: list


# ---------------------------------------------------------------------------
# Array nodes
# ---------------------------------------------------------------------------

@dataclass
class ArrayLiteral:
    """An array literal node: [expr1, expr2, ...]."""

    elements: list


@dataclass
class ArrayIndex:
    """An array indexing read node: array[index]."""

    array_expr: object
    index_expr: object


@dataclass
class ArrayAssign:
    """An array indexing write node: array[index] = value."""

    array_expr: object
    index_expr: object
    value_expr: object


# ---------------------------------------------------------------------------
# Unary node
# ---------------------------------------------------------------------------

@dataclass
class UnaryMinus:
    """Unary negation: -expr."""

    operand: object
