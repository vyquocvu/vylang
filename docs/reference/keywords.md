# Tham khảo từ khóa / Keyword Reference

Danh sách đầy đủ tất cả từ khóa trong vylang, được thiết kế tối ưu theo văn phong lập trình tiếng Việt tự nhiên.

---

## Từ khóa điều khiển / Control Flow

| Từ khóa | Tiếng Anh | Mô tả | Trạng thái |
|---|---|---|---|
| `nếu` | `if` | Thực thi khối lệnh nếu điều kiện đúng | ✅ |
| `thì` | `then` | Tiếp nối sau điều kiện của `nếu` / `khi` | ✅ |
| `ngược_lại` / `khác_thì` | `else` | Thực thi nếu tất cả điều kiện trên đều sai | ✅ |
| `khác_nếu` / `ngược_lại_nếu` | `else if` | Kiểm tra điều kiện phụ tiếp theo | ✅ |
| `nếu_không` | `unless` | Ngược lại của `nếu` (chạy khi điều kiện sai) | ✅ |
| `khi` | `while` | Vòng lặp chạy liên tục khi điều kiện đúng | ✅ |
| `cho` / `lặp` | `for` | Vòng lặp với biến đếm hoặc duyệt phần tử | ✅ |
| `trong` | `in` | Duyệt phần tử trong một tập hợp (`cho x trong y`) | ✅ |
| `đến_khi` | `until` | Vòng lặp chạy liên tục cho đến khi điều kiện đúng | ✅ |
| `ngắt` | `break` | Thoát lập tức khỏi vòng lặp | ✅ |
| `tiếp_theo` | `next/continue` | Bỏ qua phần còn lại và sang vòng lặp kế tiếp | ✅ |
| `hết` | `end` | Đánh dấu kết thúc một khối lệnh | ✅ |

---

## Từ khóa khai báo / Declaration Keywords

| Từ khóa | Tiếng Anh | Mô tả | Trạng thái |
|---|---|---|---|
| `khai_báo` | `let/var` | Khai báo biến mới | ✅ |
| `hằng_số` | `const` | Khai báo hằng số không thể thay đổi giá trị | ✅ |
| `hàm` | `def/func` | Định nghĩa hàm mới | ✅ |
| `trả_về` | `return` | Thoát hàm và trả về giá trị | ✅ |
| `lớp` | `class` | Khai báo một lớp (OOP) | ✅ |
| `kế_thừa` / `mở_rộng` | `extends` | Kế thừa từ lớp cha | ✅ |
| `bản_thân` | `self/this` | Tham chiếu tới đối tượng hiện tại | ✅ |
| `cấu_trúc` | `struct` | Định nghĩa một kiểu dữ liệu cấu trúc | ✅ |
| `giao_diện` | `interface` | Định nghĩa một giao diện / khuôn mẫu | ✅ |
| `gói` | `package/namespace`| Định nghĩa gói chứa mã nguồn | ✅ |
| `nạp` / `sử_dung` | `import/use` | Nhập thư viện hoặc module khác vào chương trình | ✅ |

---

## Quản lý ngoại lệ / Exception Handling

| Từ khóa | Tiếng Anh | Mô tả | Trạng thái |
|---|---|---|---|
| `thử` | `try` | Bắt đầu khối lệnh có thể xảy ra lỗi | ✅ |
| `bắt` / `bắt_lỗi` | `catch` | Khối lệnh xử lý khi có lỗi xảy ra | ✅ |
| `cuối_cùng` | `finally` | Luôn luôn thực thi (dù có lỗi hay không) | ✅ |
| `ném` / `ném_lỗi` | `throw/raise` | Chủ động tạo ra một ngoại lệ / lỗi | ✅ |

---

## Từ khóa giá trị / Value Keywords

| Từ khóa | Tiếng Anh | Giá trị tương đương | Trạng thái |
|---|---|---|---|
| `đúng` | `true` | Boolean true | ✅ |
| `sai` | `false` | Boolean false | ✅ |
| `trống` | `null/nil` | Giá trị trống / không xác định | ✅ |

---

## Từ khóa toán tử logic / Logical Operator Keywords

| Từ khóa | Tiếng Anh | Tương đương / Mô tả | Trạng thái |
|---|---|---|---|
| `và` | `and` | Toán tử và logic (`&&`) | ✅ |
| `hoặc` | `or` | Toán tử hoặc logic (`||`) | ✅ |
| `không` | `not` | Toán tử phủ định (`!`) | ✅ |
| `hoặc_loại` / `hoặc_loại_trừ` | `xor` | Toán tử hoặc loại trừ | ✅ |
| `là` | `is` | Kiểm tra đồng nhất đối tượng | ✅ |
| `không_là` / `không_phải_là` | `is not` | Kiểm tra không đồng nhất đối tượng | ✅ |
| `trong` | `in` | Kiểm tra sự tồn tại trong tập hợp | ✅ |
| `không_trong` / `không_ở_trong` | `not in` | Kiểm tra sự không tồn tại trong tập hợp | ✅ |

---

## Hàm dựng sẵn / Built-in Functions

| Hàm | Mô tả | Trạng thái |
|---|---|---|
| `in_ra(...)` | In giá trị ra màn hình | ✅ |
| `đọc_dòng()` | Đọc một dòng ký tự nhập từ bàn phím | ✅ |
| `kiểu(...)` | Trả về kiểu dữ liệu của biểu thức | ✅ |

---

## Chú thích trạng thái / Status Legend

| Ký hiệu | Ý nghĩa |
|---|---|
| ✅ | Đã triển khai (Implemented) |
| ✅ | Đang phát triển (In development) |
| ✅ | Kế hoạch (Planned) |
