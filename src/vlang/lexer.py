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
        # NEU_KHONG ("nếu_không" / unless) must precede NEU since it shares
        # the "nếu" prefix — otherwise NEU would greedily match first.
        self._lg.add("NEU_KHONG", r"nếu_không(?!\w)|neu_khong(?!\w)")
        self._lg.add("NEU", r"nếu|neu")
        self._lg.add("KHAC_NEU", r"khác_nếu(?!\w)|ngược_lại_nếu(?!\w)|khac_neu(?!\w)|nguoc_lai_neu(?!\w)")
        self._lg.add("KHAC_THI", r"khác_thì|khac_thi")
        self._lg.add("HAM", r"hàm|ham")
        self._lg.add("TRA_VE", r"trả_về|tra_ve")
        self._lg.add("DUNG", r"đúng|dung")
        self._lg.add("SAI", r"sai")

        # ------------------------------------------------------------------
        # Control flow: loops, break/continue (must precede IDENTIFIER)
        # ------------------------------------------------------------------
        self._lg.add("LAP", r"lặp(?!\w)|cho(?!\w)|lap(?!\w)")
        self._lg.add("TRONG", r"trong(?!\w)")
        # DEN_KHI ("đến_khi" / until) must precede DEN ("đến" / to).
        self._lg.add("DEN_KHI", r"đến_khi(?!\w)|den_khi(?!\w)")
        self._lg.add("DEN", r"đến(?!\w)|den(?!\w)")
        self._lg.add("TU", r"từ(?!\w)|tu(?!\w)")
        self._lg.add("NGAT", r"ngắt(?!\w)|ngat(?!\w)")
        self._lg.add("TIEP_THEO", r"tiếp_theo(?!\w)|tiep_theo(?!\w)")

        # ------------------------------------------------------------------
        # Declarations: const, class, struct, interface, modules, OOP
        # ------------------------------------------------------------------
        self._lg.add("HANG_SO", r"hằng_số(?!\w)|hang_so(?!\w)")
        self._lg.add("LOP", r"lớp(?!\w)|lop(?!\w)")
        self._lg.add("MO_RONG", r"mở_rộng(?!\w)|kế_thừa(?!\w)|mo_rong(?!\w)|ke_thua(?!\w)")
        self._lg.add("BAN_THAN", r"bản_thân(?!\w)|ban_than(?!\w)")
        self._lg.add("CAU_TRUC", r"cấu_trúc(?!\w)|cau_truc(?!\w)")
        self._lg.add("GIAO_DIEN", r"giao_diện(?!\w)|giao_dien(?!\w)")
        self._lg.add("GOI", r"gói(?!\w)|goi(?!\w)")
        self._lg.add("NAP", r"nạp(?!\w)|sử_dụng(?!\w)|nap(?!\w)|su_dung(?!\w)")

        # ------------------------------------------------------------------
        # Exception handling
        # ------------------------------------------------------------------
        self._lg.add("THU", r"thử(?!\w)|thu(?!\w)")
        self._lg.add("BAT", r"bắt_lỗi(?!\w)|bắt(?!\w)|bat_loi(?!\w)|bat(?!\w)")
        self._lg.add("CUOI_CUNG", r"cuối_cùng(?!\w)|cuoi_cung(?!\w)")
        self._lg.add("NEM", r"ném_lỗi(?!\w)|ném(?!\w)|nem_loi(?!\w)|nem(?!\w)")

        # ------------------------------------------------------------------
        # Value / logical-operator keywords
        # ------------------------------------------------------------------
        self._lg.add("RONG", r"trống(?!\w)|rong(?!\w)")
        self._lg.add("HOAC_LOAI", r"hoặc_loại_trừ(?!\w)|hoặc_loại(?!\w)|hoac_loai_tru(?!\w)|hoac_loai(?!\w)")
        # KHONG_LA / KHONG_TRONG must precede bare KHONG (shared prefix).
        self._lg.add("KHONG_LA", r"không_phải_là(?!\w)|không_là(?!\w)|khong_phai_la(?!\w)|khong_la(?!\w)")
        self._lg.add("KHONG_TRONG", r"không_ở_trong(?!\w)|không_trong(?!\w)|khong_o_trong(?!\w)|khong_trong(?!\w)")
        self._lg.add("KHONG", r"không(?!\w)|khong(?!\w)")
        self._lg.add("LA", r"là(?!\w)|la(?!\w)")

        # ------------------------------------------------------------------
        # Built-in functions
        # ------------------------------------------------------------------
        self._lg.add("DOC_DONG", r"đọc_dòng(?!\w)|doc_dong(?!\w)")
        self._lg.add("KIEU", r"kiểu(?!\w)|kieu(?!\w)")

        # ------------------------------------------------------------------
        # Parentheses & Delimiters
        # ------------------------------------------------------------------
        self._lg.add("MO_NGOAC_TRON", r"\(")
        self._lg.add("DONG_NGOAC_TRON", r"\)")
        self._lg.add("MO_NGOAC_VUONG", r"\[")
        self._lg.add("DONG_NGOAC_VUONG", r"\]")
        self._lg.add("PHAY", r",")
        self._lg.add("CHAM", r"\.")

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
        self._lg.add("VA",   r"&&|và(?!\w)|va(?!\w)")
        self._lg.add("HOAC", r"\|\||hoặc(?!\w)|hoac(?!\w)")

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

        # String literal: double-quoted, no escape sequences.
        self._lg.add("CHUOI", r'"[^"\n]*"')

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
