"""
Lexer for the vlang compiler.

Uses ``rply.LexerGenerator`` to tokenize .vpl source files.
Token names use Vietnamese transliterations:

    IN_RA          — in_ra  (print)
    SO_NGUYEN      — integer literal
    CONG           — +  (cộng)
    TRU            — -  (trừ)
    NHAN           — *  (nhân)
    CHIA           — /  (chia)
    BANG           — == (bằng)
    LON_HON        — >  (lớn hơn)
    NHO_HON        — <  (nhỏ hơn)
    BANG_LON_HON   — >= (bằng lớn hơn)
    BANG_NHO_HON   — <= (bằng nhỏ hơn)
    KHAC           — != (khác)
    MO_NGOAC_TRON  — (  (mở ngoặc tròn)
    DONG_NGOAC_TRON— )  (đóng ngoặc tròn)
    HET_DONG       — newline (hết dòng)
"""

from rply import LexerGenerator


class Lexer:
    """Wraps rply's LexerGenerator to produce a vlang lexer."""

    def __init__(self) -> None:
        self._lg = LexerGenerator()

    def _add_tokens(self) -> None:
        # ------------------------------------------------------------------
        # Keywords / builtins
        # ------------------------------------------------------------------
        self._lg.add("IN_RA", r"in_ra")
        self._lg.add("KHAI_BAO", r"khai_báo|khai_bao")
        self._lg.add("KHI", r"khi")
        self._lg.add("THI", r"thì|thi")
        self._lg.add("KET_THUC", r"hết|het")
        self._lg.add("NEU", r"nếu|neu")
        self._lg.add("KHAC_THI", r"khác_thì|khac_thi")
        self._lg.add("HAM", r"hàm|ham")
        self._lg.add("TRA_VE", r"trả_về|tra_ve")
        self._lg.add("DUNG", r"đúng|dung")
        self._lg.add("SAI", r"sai")

        # ------------------------------------------------------------------
        # Parentheses & Delimiters
        # ------------------------------------------------------------------
        self._lg.add("MO_NGOAC_TRON", r"\(")
        self._lg.add("DONG_NGOAC_TRON", r"\)")
        self._lg.add("MO_NGOAC_VUONG", r"\[")
        self._lg.add("DONG_NGOAC_VUONG", r"\]")
        self._lg.add("PHAY", r",")

        # ------------------------------------------------------------------
        # Comparison operators  (longer patterns must come before shorter ones)
        # ------------------------------------------------------------------
        self._lg.add("BANG",          r"==")
        self._lg.add("BANG_LON_HON",  r">=")
        self._lg.add("BANG_NHO_HON",  r"<=")
        self._lg.add("KHAC",          r"!=")
        self._lg.add("LON_HON",       r">")
        self._lg.add("NHO_HON",       r"<")   # Fixed: was 'NHO_HON)' (stray paren)
        self._lg.add("GAN",           r"=")

        # ------------------------------------------------------------------
        # Logical operators (must precede identifiers)
        # ------------------------------------------------------------------
        self._lg.add("VA",   r"&&")
        self._lg.add("HOAC", r"\|\|")

        # ------------------------------------------------------------------
        # Arithmetic operators
        # ------------------------------------------------------------------
        self._lg.add("CONG", r"\+")
        self._lg.add("TRU",  r"\-")
        self._lg.add("NHAN", r"\*")
        self._lg.add("CHIA", r"\/")
        self._lg.add("CHIA_DU", r"\%")

        # Float literals must come before integers to avoid "3" matching "3.14"
        self._lg.add("SO_THUC", r"\d+\.\d+")
        self._lg.add("SO_NGUYEN", r"\d+")

        # ------------------------------------------------------------------
        # Identifiers (supporting Unicode / accented Vietnamese)
        # ------------------------------------------------------------------
        self._lg.add("IDENTIFIER", r"[^\W\d][\w]*")

        # ------------------------------------------------------------------
        # Statement terminator — newline (or CRLF)
        # ------------------------------------------------------------------
        self._lg.add("HET_DONG", r"(\n)|(\r\n)")

        # ------------------------------------------------------------------
        # Comments (ignored)
        # ------------------------------------------------------------------
        self._lg.ignore(r"#[^\n]*")

        # ------------------------------------------------------------------
        self._lg.ignore(r"[ \t]+")

    def get_lexer(self):
        """Build and return the rply lexer object."""
        self._add_tokens()
        return self._lg.build()
