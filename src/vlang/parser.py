"""
LALR parser for the vlang compiler.

Uses ``rply.ParserGenerator`` to build a bottom-up parser from the token
stream produced by ``vlang.lexer.Lexer``.
"""

from rply import ParserGenerator

from vlang.nodes import (
    Number,
    Float,
    Boolean,
    Sum,
    Sub,
    Print,
    Mul,
    Div,
    Mod,
    Program,
    EmptyStatement,
    VarDecl,
    VarAssign,
    VarRef,
    Compare,
    WhileLoop,
    IfStmt,
    FuncDef,
    ReturnStmt,
    CallExpr,
    ArrayLiteral,
    ArrayIndex,
    ArrayAssign,
    LogicalAnd,
    LogicalOr,
    LogicalXor,
    UnaryMinus,
    UnaryNot,
    StringLiteral,
    NullLiteral,
    ConstDecl,
    IsCompare,
    InCompare,
    ForRangeLoop,
    ForInLoop,
    UntilLoop,
    UnlessStmt,
    BreakStmt,
    ContinueStmt,
    ThrowStmt,
    TryStmt,
    PackageDecl,
    ImportStmt,
    FieldDecl,
    ClassDef,
    StructDef,
    InterfaceDef,
    AttrAccess,
    AttrAssign,
    MethodCall,
    ReadLineExpr,
    TypeOfExpr,
)

# All token names the parser may encounter.
_TOKENS = [
    "SO_NGUYEN",
    "SO_THUC",
    "CHUOI",
    "IN_RA",
    "KHAI_BAO",
    "KHI",
    "THI",
    "KET_THUC",
    "GAN",
    "NEU",
    "NEU_KHONG",
    "KHAC_NEU",
    "KHAC_THI",
    "HAM",
    "TRA_VE",
    "PHAY",
    "MO_NGOAC_TRON",
    "DONG_NGOAC_TRON",
    "HET_DONG",
    "CONG",
    "TRU",
    "NHAN",
    "CHIA",
    "CHIA_DU",
    "BANG",
    "BANG_LON_HON",
    "BANG_NHO_HON",
    "KHAC",
    "LON_HON",
    "NHO_HON",
    "IDENTIFIER",
    "DUNG",
    "SAI",
    "MO_NGOAC_VUONG",
    "DONG_NGOAC_VUONG",
    "VA",
    "HOAC",
    "HOAC_LOAI",
    "LA",
    "KHONG_LA",
    "KHONG",
    "TRONG",
    "KHONG_TRONG",
    "RONG",
    "CHAM",
    "LAP",
    "DEN",
    "DEN_KHI",
    "TU",
    "NGAT",
    "TIEP_THEO",
    "HANG_SO",
    "LOP",
    "MO_RONG",
    "BAN_THAN",
    "CAU_TRUC",
    "GIAO_DIEN",
    "GOI",
    "NAP",
    "THU",
    "BAT",
    "CUOI_CUNG",
    "NEM",
    "DOC_DONG",
    "KIEU",
]

# Operator precedence (low → high, left-associative by default).
_PRECEDENCE = [
    ("left", ["HOAC", "HOAC_LOAI"]),
    ("left", ["VA"]),
    ("left", ["LA", "KHONG_LA", "TRONG", "KHONG_TRONG"]),
    ("left", ["BANG", "BANG_LON_HON", "BANG_NHO_HON", "KHAC", "LON_HON", "NHO_HON"]),
    ("left", ["CONG", "TRU"]),
    ("left", ["NHAN", "CHIA", "CHIA_DU"]),
    ("right", ["UMINUS", "UNOT"]),
    ("left", ["MO_NGOAC_VUONG"]),
]


class Parser:
    """Builds an LALR parser that emits a pure-data AST (see ``vlang.nodes``)."""

    def __init__(self) -> None:
        self._pg = ParserGenerator(_TOKENS, precedence=_PRECEDENCE)

    def parse(self) -> None:
        """Register all grammar productions with rply decorators."""

        @self._pg.production("program : statements")
        def program(p):
            return p[0]

        @self._pg.production("statements : statement")
        def statements_single(p):
            return Program([p[0]])

        @self._pg.production("statements : statements statement")
        def statements_multiple(p):
            p[0].add_statement(p[1])
            return p[0]

        @self._pg.production("statement : IN_RA MO_NGOAC_TRON expression DONG_NGOAC_TRON HET_DONG")
        def statement_print(p):
            return Print(p[2])

        @self._pg.production("statement : expression HET_DONG")
        def statement_expr(p):
            return p[0]

        @self._pg.production("statement : KHAI_BAO IDENTIFIER GAN expression HET_DONG")
        def statement_khai_bao(p):
            return VarDecl(p[1].value, p[3])

        @self._pg.production("statement : HANG_SO IDENTIFIER GAN expression HET_DONG")
        def statement_const(p):
            return ConstDecl(p[1].value, p[3])

        @self._pg.production("statement : IDENTIFIER GAN expression HET_DONG")
        def statement_assign(p):
            return VarAssign(p[0].value, p[2])

        @self._pg.production("statement : expression MO_NGOAC_VUONG expression DONG_NGOAC_VUONG GAN expression HET_DONG")
        def statement_array_assign(p):
            return ArrayAssign(p[0], p[2], p[5])

        @self._pg.production("statement : IDENTIFIER CHAM IDENTIFIER GAN expression HET_DONG")
        def statement_attr_assign(p):
            return AttrAssign(p[0].value, p[2].value, p[4])

        @self._pg.production("statement : BAN_THAN CHAM IDENTIFIER GAN expression HET_DONG")
        def statement_self_attr_assign(p):
            return AttrAssign("bản_thân", p[2].value, p[4])

        @self._pg.production("statement : KHI expression THI HET_DONG statements KET_THUC HET_DONG")
        def statement_while(p):
            return WhileLoop(p[1], p[4])

        @self._pg.production("statement : DEN_KHI expression THI HET_DONG statements KET_THUC HET_DONG")
        def statement_until(p):
            return UntilLoop(p[1], p[4])

        @self._pg.production("statement : LAP IDENTIFIER TU expression DEN expression THI HET_DONG statements KET_THUC HET_DONG")
        def statement_for_range(p):
            return ForRangeLoop(p[1].value, p[3], p[5], p[8])

        @self._pg.production("statement : LAP IDENTIFIER TRONG IDENTIFIER THI HET_DONG statements KET_THUC HET_DONG")
        def statement_for_in(p):
            return ForInLoop(p[1].value, p[3].value, p[6])

        @self._pg.production("statement : NGAT HET_DONG")
        def statement_break(p):
            return BreakStmt()

        @self._pg.production("statement : TIEP_THEO HET_DONG")
        def statement_continue(p):
            return ContinueStmt()

        @self._pg.production("statement : NEU expression THI HET_DONG statements elif_tail KET_THUC HET_DONG")
        def statement_if(p):
            return IfStmt(p[1], p[4], p[5])

        @self._pg.production("elif_tail : ")
        def elif_tail_empty(p):
            return None

        @self._pg.production("elif_tail : KHAC_THI HET_DONG statements")
        def elif_tail_else(p):
            return p[2]

        @self._pg.production("elif_tail : KHAC_NEU expression THI HET_DONG statements elif_tail")
        def elif_tail_elif(p):
            return IfStmt(p[1], p[4], p[5])

        @self._pg.production("statement : NEU_KHONG expression THI HET_DONG statements KET_THUC HET_DONG")
        def statement_unless(p):
            return UnlessStmt(p[1], p[4])

        @self._pg.production("statement : HAM IDENTIFIER MO_NGOAC_TRON param_list DONG_NGOAC_TRON HET_DONG statements KET_THUC HET_DONG")
        def statement_func_def(p):
            return FuncDef(p[1].value, p[3], p[6])

        @self._pg.production("statement : TRA_VE expression HET_DONG")
        def statement_return(p):
            return ReturnStmt(p[1])

        @self._pg.production("statement : NEM expression HET_DONG")
        def statement_throw(p):
            return ThrowStmt(p[1])

        @self._pg.production("statement : THU THI HET_DONG statements BAT IDENTIFIER THI HET_DONG statements KET_THUC HET_DONG")
        def statement_try_catch(p):
            return TryStmt(p[3], p[5].value, p[8], None)

        @self._pg.production("statement : THU THI HET_DONG statements BAT IDENTIFIER THI HET_DONG statements CUOI_CUNG THI HET_DONG statements KET_THUC HET_DONG")
        def statement_try_catch_finally(p):
            return TryStmt(p[3], p[5].value, p[8], p[12])

        @self._pg.production("statement : GOI IDENTIFIER HET_DONG")
        def statement_package(p):
            return PackageDecl(p[1].value)

        @self._pg.production("statement : NAP CHUOI HET_DONG")
        def statement_import(p):
            return ImportStmt(p[1].value[1:-1])

        @self._pg.production("statement : LOP IDENTIFIER THI HET_DONG class_body KET_THUC HET_DONG")
        def statement_class_def(p):
            fields = [m for m in p[4] if isinstance(m, FieldDecl)]
            methods = [m for m in p[4] if isinstance(m, FuncDef)]
            return ClassDef(p[1].value, None, fields, methods)

        @self._pg.production("statement : LOP IDENTIFIER MO_RONG IDENTIFIER THI HET_DONG class_body KET_THUC HET_DONG")
        def statement_class_def_extends(p):
            fields = [m for m in p[6] if isinstance(m, FieldDecl)]
            methods = [m for m in p[6] if isinstance(m, FuncDef)]
            return ClassDef(p[1].value, p[3].value, fields, methods)

        @self._pg.production("class_body : ")
        def class_body_empty(p):
            return []

        @self._pg.production("class_body : class_body HET_DONG")
        def class_body_blank(p):
            return p[0]

        @self._pg.production("class_body : class_body KHAI_BAO IDENTIFIER GAN expression HET_DONG")
        def class_body_field(p):
            p[0].append(FieldDecl(p[2].value, p[4]))
            return p[0]

        @self._pg.production(
            "class_body : class_body HAM IDENTIFIER MO_NGOAC_TRON param_list DONG_NGOAC_TRON "
            "HET_DONG statements KET_THUC HET_DONG"
        )
        def class_body_method(p):
            p[0].append(FuncDef(p[2].value, p[4], p[7]))
            return p[0]

        @self._pg.production("statement : CAU_TRUC IDENTIFIER THI HET_DONG struct_body KET_THUC HET_DONG")
        def statement_struct_def(p):
            return StructDef(p[1].value, p[4])

        @self._pg.production("struct_body : ")
        def struct_body_empty(p):
            return []

        @self._pg.production("struct_body : struct_body HET_DONG")
        def struct_body_blank(p):
            return p[0]

        @self._pg.production("struct_body : struct_body KHAI_BAO IDENTIFIER GAN expression HET_DONG")
        def struct_body_field(p):
            p[0].append(FieldDecl(p[2].value, p[4]))
            return p[0]

        @self._pg.production("statement : GIAO_DIEN IDENTIFIER THI HET_DONG interface_body KET_THUC HET_DONG")
        def statement_interface_def(p):
            return InterfaceDef(p[1].value, p[4])

        @self._pg.production("interface_body : ")
        def interface_body_empty(p):
            return []

        @self._pg.production("interface_body : interface_body HET_DONG")
        def interface_body_blank(p):
            return p[0]

        @self._pg.production(
            "interface_body : interface_body HAM IDENTIFIER MO_NGOAC_TRON param_list DONG_NGOAC_TRON HET_DONG"
        )
        def interface_body_method(p):
            p[0].append(p[2].value)
            return p[0]

        @self._pg.production("statement : HET_DONG")
        def statement_empty(p):
            return EmptyStatement()

        @self._pg.production("expression : expression NHAN expression")
        @self._pg.production("expression : expression CHIA expression")
        @self._pg.production("expression : expression CHIA_DU expression")
        @self._pg.production("expression : expression CONG expression")
        @self._pg.production("expression : expression TRU  expression")
        def expression(p):
            left, op, right = p[0], p[1], p[2]
            token = op.gettokentype()
            if token == "NHAN":
                return Mul(left, right)
            if token == "CHIA":
                return Div(left, right)
            if token == "CHIA_DU":
                return Mod(left, right)
            if token == "CONG":
                return Sum(left, right)
            if token == "TRU":
                return Sub(left, right)
            raise ValueError(f"Unknown operator token: {token}")

        @self._pg.production("expression : expression BANG expression")
        @self._pg.production("expression : expression BANG_LON_HON expression")
        @self._pg.production("expression : expression BANG_NHO_HON expression")
        @self._pg.production("expression : expression KHAC expression")
        @self._pg.production("expression : expression LON_HON expression")
        @self._pg.production("expression : expression NHO_HON expression")
        def expression_compare(p):
            left, op, right = p[0], p[1], p[2]
            return Compare(left, op.gettokentype(), right)

        @self._pg.production("expression : expression VA expression")
        def expression_and(p):
            return LogicalAnd(p[0], p[2])

        @self._pg.production("expression : expression HOAC expression")
        def expression_or(p):
            return LogicalOr(p[0], p[2])

        @self._pg.production("expression : expression HOAC_LOAI expression")
        def expression_xor(p):
            return LogicalXor(p[0], p[2])

        @self._pg.production("expression : expression LA expression")
        def expression_is(p):
            return IsCompare(p[0], p[2], negate=False)

        @self._pg.production("expression : expression KHONG_LA expression")
        def expression_is_not(p):
            return IsCompare(p[0], p[2], negate=True)

        @self._pg.production("expression : expression TRONG IDENTIFIER", precedence="TRONG")
        def expression_in(p):
            return InCompare(p[0], p[2].value, negate=False)

        @self._pg.production("expression : expression KHONG_TRONG IDENTIFIER", precedence="KHONG_TRONG")
        def expression_not_in(p):
            return InCompare(p[0], p[2].value, negate=True)

        @self._pg.production("expression : TRU expression", precedence="UMINUS")
        def expression_unary_minus(p):
            return UnaryMinus(p[1])

        @self._pg.production("expression : KHONG expression", precedence="UNOT")
        def expression_not(p):
            return UnaryNot(p[1])

        @self._pg.production("expression : IDENTIFIER")
        def expression_var(p):
            return VarRef(p[0].value)

        @self._pg.production("expression : BAN_THAN")
        def expression_self(p):
            return VarRef("bản_thân")

        @self._pg.production("expression : RONG")
        def expression_null(p):
            return NullLiteral()

        @self._pg.production("expression : CHUOI")
        def expression_string(p):
            return StringLiteral(p[0].value[1:-1])

        @self._pg.production("expression : IDENTIFIER MO_NGOAC_TRON arg_list DONG_NGOAC_TRON")
        def expression_call(p):
            return CallExpr(p[0].value, p[2])

        @self._pg.production("expression : DOC_DONG MO_NGOAC_TRON DONG_NGOAC_TRON")
        def expression_read_line(p):
            return ReadLineExpr()

        @self._pg.production("expression : KIEU MO_NGOAC_TRON expression DONG_NGOAC_TRON")
        def expression_type_of(p):
            return TypeOfExpr(p[2])

        @self._pg.production("expression : IDENTIFIER CHAM IDENTIFIER")
        def expression_attr_access(p):
            return AttrAccess(p[0].value, p[2].value)

        @self._pg.production("expression : BAN_THAN CHAM IDENTIFIER")
        def expression_self_attr_access(p):
            return AttrAccess("bản_thân", p[2].value)

        @self._pg.production("expression : IDENTIFIER CHAM IDENTIFIER MO_NGOAC_TRON arg_list DONG_NGOAC_TRON")
        def expression_method_call(p):
            return MethodCall(p[0].value, p[2].value, p[4])

        @self._pg.production("expression : BAN_THAN CHAM IDENTIFIER MO_NGOAC_TRON arg_list DONG_NGOAC_TRON")
        def expression_self_method_call(p):
            return MethodCall("bản_thân", p[2].value, p[4])

        @self._pg.production("expression : SO_NGUYEN")
        def number(p):
            return Number(p[0].value)

        @self._pg.production("expression : SO_THUC")
        def float_literal(p):
            return Float(p[0].value)

        @self._pg.production("expression : DUNG")
        def expression_dung(p):
            return Boolean(True)

        @self._pg.production("expression : SAI")
        def expression_sai(p):
            return Boolean(False)

        @self._pg.production("expression : MO_NGOAC_TRON expression DONG_NGOAC_TRON")
        def expression_parens(p):
            return p[1]

        @self._pg.production("expression : MO_NGOAC_VUONG arg_list DONG_NGOAC_VUONG")
        def expression_array_literal(p):
            return ArrayLiteral(p[1])

        @self._pg.production("expression : expression MO_NGOAC_VUONG expression DONG_NGOAC_VUONG")
        def expression_array_index(p):
            return ArrayIndex(p[0], p[2])

        # Parameter list helpers
        @self._pg.production("param_list : ")
        def param_list_empty(p):
            return []

        @self._pg.production("param_list : IDENTIFIER")
        def param_list_single(p):
            return [p[0].value]

        @self._pg.production("param_list : param_list PHAY IDENTIFIER")
        def param_list_multiple(p):
            p[0].append(p[2].value)
            return p[0]

        # Argument list helpers
        @self._pg.production("arg_list : ")
        def arg_list_empty(p):
            return []

        @self._pg.production("arg_list : expression")
        def arg_list_single(p):
            return [p[0]]

        @self._pg.production("arg_list : arg_list PHAY expression")
        def arg_list_multiple(p):
            p[0].append(p[2])
            return p[0]

        @self._pg.error
        def error_handle(token):
            pos = token.source_pos
            if pos is not None:
                raise SyntaxError(
                    f"Lỗi cú pháp tại dòng {pos.lineno}, cột {pos.colno}: "
                    f"không thể xử lý '{token.value}'"
                )
            raise SyntaxError(f"Lỗi cú pháp: không thể xử lý '{token.value}'")

    def get_parser(self):
        """Build and return the rply parser object."""
        return self._pg.build()
