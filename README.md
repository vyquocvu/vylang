# vylang — Ngôn ngữ lập trình tiếng Việt 🇻🇳

> A hobby compiler for a Vietnamese-keyword programming language, targeting native binaries via LLVM.  
> *Thích thì làm thôi!*

---

## Setup

**Requirements:** Python ≥ 3.10, `llc` (LLVM), `gcc`

```bash
# 1. Clone
git clone https://github.com/vyquocvu/vylang.git
cd vylang

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install (editable mode includes the `vlang` CLI)
pip install -e ".[dev]"
```

---

## Usage

```bash
# Emit LLVM IR only
vlang compile examples/hello.vpl

# Compile + link to a native binary
vlang compile examples/hello.vpl -o hello
./hello

# Or use the convenience script
chmod +x scripts/build.sh
./scripts/build.sh examples/hello.vpl hello
```

---

## Project Structure

```
vylang/
├── src/vlang/
│   ├── __init__.py   # Package version
│   ├── lexer.py      # Tokeniser (rply)
│   ├── parser.py     # LALR parser (rply)
│   ├── nodes.py      # AST node classes (llvmlite IR emitters)
│   ├── codegen.py    # LLVM module / execution engine setup
│   └── cli.py        # `vlang` CLI entry point
├── examples/
│   └── hello.vpl     # Sample program
├── tests/
│   └── test_lexer.py # Lexer unit tests
├── scripts/
│   └── build.sh      # Compile + link helper
└── pyproject.toml    # Package metadata & tooling config
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Từ khóa (Keywords)

| Từ khóa | Tiếng Anh | Ý nghĩa |
|---|---|---|
| `in_ra` | print | In giá trị ra màn hình |
| `và` | and | Toán tử logic `&&` |
| `ngắt` | break | Thoát khỏi vòng lặp |
| `lớp` | class | Định nghĩa lớp |
| `hàm` | def / func | Định nghĩa hàm |
| `hằng_số` | const | Khai báo hằng số |
| `hết` | end | Kết thúc khối lệnh |
| `khai_báo` | let / var | Khai báo biến mới |
| `sai` | false | Giá trị boolean false |
| `lặp` | for | Vòng lặp for |
| `nếu` | if | Điều kiện if |
| `khác_thì` | else | Điều kiện else |
| `tiếp_theo` | next | Nhảy sang vòng lặp tiếp theo |
| `trống` | null / nil | Giá trị trống/null |
| `không` | not | Phủ định logic `!` |
| `hoặc` | or | Toán tử logic `\|\|` |
| `trả_về` | return | Trả về giá trị |
| `thì` | then | Tiếp nối điều kiện |
| `đúng` | true | Giá trị boolean true |
| `nếu_không` | unless | Ngược lại của nếu |
| `đến_khi` | until | Lặp đến khi điều kiện đúng |
| `khi` | while | Lặp khi điều kiện đúng |
| `mở_rộng` | extends | Kế thừa lớp cha |
| `bản_thân` | self | Đối tượng hiện tại |

## Toán tử (Operators)

```
+   cộng          -   trừ
*   nhân          /   chia (thập phân)
\   chia nguyên   %   chia lấy dư
=   gán           ==  bằng
<   nhỏ hơn       >   lớn hơn
<=  nhỏ hơn/bằng  >=  lớn hơn/bằng
!=  khác          &&  và
!   phủ định      ||  hoặc
new khởi tạo
```

## Ví dụ (Examples)

```
# Khai báo lớp
lớp cafe {
  vị = 'ngon'
  màu = 'đen'
}

# Khai báo hàm
hàm nhân_đôi (x) {
  trả_về x * 2
}

# In ra kết quả
in_ra(4 + 4 - 2)
```

---

## Manual Build Steps (without the CLI)

```bash
python -m vlang.cli compile examples/hello.vpl
llc -filetype=obj -relocation-model=pic output.ll
gcc output.o -o output
./output
```
