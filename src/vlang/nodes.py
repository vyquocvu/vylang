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


@dataclass
class UnaryNot:
    """Logical negation: không expr  (!expr)."""

    operand: object


# ---------------------------------------------------------------------------
# String literal
# ---------------------------------------------------------------------------

@dataclass
class StringLiteral:
    """A double-quoted string literal node. ``value`` excludes the quotes."""

    value: str


# ---------------------------------------------------------------------------
# Value keywords
# ---------------------------------------------------------------------------

@dataclass
class NullLiteral:
    """The null/nil value node: trống."""


# ---------------------------------------------------------------------------
# Const declaration
# ---------------------------------------------------------------------------

@dataclass
class ConstDecl:
    """Constant declaration node: hằng_số name = expr (immutable after this)."""

    name: str
    expr: object


# ---------------------------------------------------------------------------
# Extra logical / comparison operators
# ---------------------------------------------------------------------------

@dataclass
class LogicalXor(BinaryOp):
    """Logical XOR: left hoặc_loại right."""


@dataclass
class IsCompare:
    """Identity comparison node: left là right / left không_là right."""

    left: object
    right: object
    negate: bool = False


@dataclass
class InCompare:
    """Membership test node: expr trong array_name / expr không_trong array_name.

    ``array_name`` must refer to a variable declared from an array literal so
    its length is known at compile time.
    """

    value: object
    array_name: str
    negate: bool = False


# ---------------------------------------------------------------------------
# Loop control flow
# ---------------------------------------------------------------------------

@dataclass
class ForRangeLoop:
    """Counting for-loop: lặp var từ start đến end thì ... hết."""

    var: str
    start: object
    end: object
    body: object


@dataclass
class ForInLoop:
    """For-each loop over an array variable: lặp var trong array_name thì ... hết."""

    var: str
    array_name: str
    body: object


@dataclass
class UntilLoop:
    """Until loop: đến_khi condition thì ... hết (loops while condition is false)."""

    condition: object
    body: object


@dataclass
class UnlessStmt:
    """Unless statement: nếu_không condition thì ... hết (runs when condition is false)."""

    condition: object
    body: object


@dataclass
class BreakStmt:
    """Break statement: ngắt."""


@dataclass
class ContinueStmt:
    """Continue/next statement: tiếp_theo."""


# ---------------------------------------------------------------------------
# Exception handling
# ---------------------------------------------------------------------------

@dataclass
class ThrowStmt:
    """Throw statement: ném expr / ném_lỗi expr."""

    expr: object


@dataclass
class TryStmt:
    """Try/catch/finally statement: thử ... bắt name ... [cuối_cùng ...] hết."""

    try_body: object
    catch_var: str
    catch_body: object
    finally_body: object = None


# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------

@dataclass
class PackageDecl:
    """Package declaration node: gói name (declarative only)."""

    name: str


@dataclass
class ImportStmt:
    """Import statement node: nạp "path" (expanded inline before codegen)."""

    path: str


# ---------------------------------------------------------------------------
# OOP: classes, structs, interfaces
# ---------------------------------------------------------------------------

@dataclass
class FieldDecl:
    """A field declaration inside a class/struct body: khai_báo name = expr."""

    name: str
    expr: object


@dataclass
class ClassDef:
    """Class definition node: lớp name [mở_rộng parent] thì ... hết."""

    name: str
    parent: str | None
    fields: list
    methods: list


@dataclass
class StructDef:
    """Struct definition node: cấu_trúc name thì ... hết (fields only)."""

    name: str
    fields: list


@dataclass
class InterfaceDef:
    """Interface definition node: giao_diện name thì ... hết (method signatures only).

    Purely declarative: vylang has no ``implements`` keyword, so interfaces
    are registered but not enforced against classes.
    """

    name: str
    method_names: list


@dataclass
class AttrAccess:
    """Field read node: obj.field / bản_thân.field."""

    obj_name: str
    field: str


@dataclass
class AttrAssign:
    """Field write node: obj.field = expr / bản_thân.field = expr."""

    obj_name: str
    field: str
    expr: object


@dataclass
class MethodCall:
    """Method call node: obj.method(args) / bản_thân.method(args)."""

    obj_name: str
    method: str
    args: list


# ---------------------------------------------------------------------------
# Built-in functions
# ---------------------------------------------------------------------------

@dataclass
class ReadLineExpr:
    """Read-a-line-from-stdin builtin: đọc_dòng()."""


@dataclass
class TypeOfExpr:
    """Compile-time type-name builtin: kiểu(expr)."""

    expr: object
