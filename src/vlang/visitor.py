"""
LLVM IR code generation visitor for the vlang compiler.

``CodeGenVisitor`` walks the pure-data AST defined in ``vlang.nodes`` and
emits LLVM IR via an llvmlite ``IRBuilder``. Keeping emission here (rather
than on the nodes themselves) separates the AST from codegen, which makes
room for a future type-checking pass and multiple value types.

Dispatch is by node class name: a ``Foo`` node is handled by ``visit_Foo``.
The ``env`` mapping (name -> LLVM pointer / function) is threaded through
``visit`` so that nested scopes (e.g. function bodies) can use a distinct
environment without disturbing the caller's.
"""

from __future__ import annotations

from llvmlite import ir

from vlang.nodes import VarDecl, ArrayLiteral, CallExpr, FuncDef, VarRef

_I64 = ir.IntType(64)
_I32 = ir.IntType(32)
_I1 = ir.IntType(1)
_I8 = ir.IntType(8)
_F64 = ir.DoubleType()


class CodeGenVisitor:
    """Emits LLVM IR for an AST using the provided module/builder/printf."""

    def __init__(self, module: ir.Module, builder: ir.IRBuilder, printf: ir.Function) -> None:
        self.module = module
        self.builder = builder
        self.printf = printf
        # name -> {struct_type, field_order, field_defaults, methods_owner, parent}
        self.classes: dict = {}
        # name -> list[str] of method signatures (declarative only, no codegen)
        self.interfaces: dict = {}
        self._str_counter = 0

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def generate(self, node) -> None:
        """Walk *node* (typically a ``Program``) starting with a fresh scope."""
        return self.visit(node, {})

    def visit(self, node, env: dict):
        method = getattr(self, "visit_" + type(node).__name__, None)
        if method is None:
            raise NotImplementedError(f"No visitor for {type(node).__name__}")
        return method(node, env)

    # ------------------------------------------------------------------
    # Type helpers
    # ------------------------------------------------------------------

    def _to_bool(self, val: ir.Value) -> ir.Value:
        """Coerce any LLVM value to i1 (bool) for use in branch conditions."""
        if val.type == _I1:
            return val
        if val.type == _F64:
            return self.builder.fcmp_ordered("!=", val, ir.Constant(_F64, 0.0))
        return self.builder.icmp_signed("!=", val, ir.Constant(val.type, 0))

    def _promote(self, left: ir.Value, right: ir.Value):
        """Promote int operand(s) to f64 when either side is a float."""
        if left.type == _F64 or right.type == _F64:
            if left.type != _F64:
                left = self.builder.sitofp(left, _F64)
            if right.type != _F64:
                right = self.builder.sitofp(right, _F64)
        return left, right

    def _fmt_global(self, name: str, fmt: str) -> ir.GlobalVariable:
        """Return (creating if needed) a module-level constant string for printf."""
        if name in self.module.globals:
            return self.module.get_global(name)
        c_fmt = ir.Constant(
            ir.ArrayType(_I8, len(fmt)),
            bytearray(fmt.encode("utf8")),
        )
        gv = ir.GlobalVariable(self.module, c_fmt.type, name=name)
        gv.linkage = "internal"
        gv.global_constant = True
        gv.initializer = c_fmt
        return gv

    def _string_global(self, text: str) -> ir.Value:
        """Create a fresh global constant for *text* and return an i8* pointer to it."""
        self._str_counter += 1
        name = f"vlang_str_{self._str_counter}"
        data = (text + "\0").encode("utf8")
        c_str = ir.Constant(ir.ArrayType(_I8, len(data)), bytearray(data))
        gv = ir.GlobalVariable(self.module, c_str.type, name=name)
        gv.linkage = "internal"
        gv.global_constant = True
        gv.initializer = c_str
        return self.builder.bitcast(gv, _I8.as_pointer())

    def _get_extern(self, name: str, func_type: ir.FunctionType) -> ir.Function:
        """Return (declaring if needed) an external C function in the module."""
        if name in self.module.globals:
            return self.module.get_global(name)
        return ir.Function(self.module, func_type, name=name)

    def _error_globals(self):
        """Return (err_flag_ptr, err_value_ptr) module-level globals for exceptions."""
        if "vlang_err_flag" not in self.module.globals:
            flag = ir.GlobalVariable(self.module, _I1, name="vlang_err_flag")
            flag.linkage = "internal"
            flag.initializer = ir.Constant(_I1, 0)
            value = ir.GlobalVariable(self.module, _I64, name="vlang_err_value")
            value.linkage = "internal"
            value.initializer = ir.Constant(_I64, 0)
        return self.module.get_global("vlang_err_flag"), self.module.get_global("vlang_err_value")

    def _to_i64(self, val: ir.Value) -> ir.Value:
        """Best-effort coercion of any value to i64 (for struct fields / error values)."""
        if val.type == _I64:
            return val
        if val.type == _I1:
            return self.builder.zext(val, _I64)
        if val.type == _F64:
            return self.builder.fptosi(val, _I64)
        if isinstance(val.type, ir.PointerType):
            return self.builder.ptrtoint(val, _I64)
        raise ValueError(f"Không thể chuyển kiểu {val.type} sang i64")

    def _match_pointer(self, val: ir.Value, target_type: ir.Type) -> ir.Value:
        """Bitcast *val* to *target_type* when both are differing pointer types.

        Lets ``trống`` (a generic i8* null) be compared/assigned against any
        other pointer-typed value (arrays, objects).
        """
        if (
            isinstance(val.type, ir.PointerType)
            and isinstance(target_type, ir.PointerType)
            and val.type != target_type
        ):
            return self.builder.bitcast(val, target_type)
        return val

    # ------------------------------------------------------------------
    # Primitive nodes
    # ------------------------------------------------------------------

    def visit_Number(self, node, env):
        return ir.Constant(_I64, int(node.value))

    def visit_Float(self, node, env):
        return ir.Constant(_F64, float(node.value))

    def visit_Boolean(self, node, env):
        return ir.Constant(_I1, 1 if node.value else 0)

    # ------------------------------------------------------------------
    # Binary arithmetic
    # ------------------------------------------------------------------

    def visit_Sum(self, node, env):
        left, right = self._promote(self.visit(node.left, env), self.visit(node.right, env))
        return self.builder.fadd(left, right) if left.type == _F64 else self.builder.add(left, right)

    def visit_Sub(self, node, env):
        left, right = self._promote(self.visit(node.left, env), self.visit(node.right, env))
        return self.builder.fsub(left, right) if left.type == _F64 else self.builder.sub(left, right)

    def visit_Mul(self, node, env):
        left, right = self._promote(self.visit(node.left, env), self.visit(node.right, env))
        return self.builder.fmul(left, right) if left.type == _F64 else self.builder.mul(left, right)

    def visit_Div(self, node, env):
        left, right = self._promote(self.visit(node.left, env), self.visit(node.right, env))
        return self.builder.fdiv(left, right) if left.type == _F64 else self.builder.sdiv(left, right)

    def visit_Mod(self, node, env):
        left, right = self._promote(self.visit(node.left, env), self.visit(node.right, env))
        return self.builder.frem(left, right) if left.type == _F64 else self.builder.srem(left, right)

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def visit_Print(self, node, env):
        value = self.visit(node.value, env)

        voidptr_ty = _I8.as_pointer()
        if value.type == _F64:
            gv = self._fmt_global("fstr_float", "%g\n\0")
        elif value.type == _I8.as_pointer():
            gv = self._fmt_global("fstr_str", "%s\n\0")
            null_str = self._string_global("trống")
            is_null = self.builder.icmp_unsigned(
                "==", value, ir.Constant(_I8.as_pointer(), None)
            )
            value = self.builder.select(is_null, null_str, value)
        else:
            gv = self._fmt_global("fstr", "%i\n\0")

        fmt_arg = self.builder.bitcast(gv, voidptr_ty)
        self.builder.call(self.printf, [fmt_arg, value])

    def visit_Program(self, node, env):
        for stmt in node.statements:
            if self.builder.block.is_terminated:
                break
            self.visit(stmt, env)

    def visit_EmptyStatement(self, node, env):
        pass

    # ------------------------------------------------------------------
    # Variables
    # ------------------------------------------------------------------

    def visit_VarDecl(self, node, env):
        val = self.visit(node.expr, env)
        ptr = self.builder.alloca(val.type, name=node.name)
        self.builder.store(val, ptr)
        env[node.name] = ptr
        if isinstance(node.expr, ArrayLiteral):
            env["__len__:" + node.name] = len(node.expr.elements)
        if isinstance(node.expr, CallExpr) and node.expr.name in self.classes:
            env["__class__:" + node.name] = node.expr.name

    def visit_ConstDecl(self, node, env):
        self.visit_VarDecl(VarDecl(node.name, node.expr), env)
        env["__const__:" + node.name] = True

    def visit_VarAssign(self, node, env):
        if node.name not in env:
            raise ValueError(f"Biến chưa được khai báo: {node.name}")
        if env.get("__const__:" + node.name):
            raise ValueError(f"Không thể gán lại hằng_số: {node.name}")
        ptr = env[node.name]
        val = self.visit(node.expr, env)
        val = self._match_pointer(val, ptr.type.pointee)
        self.builder.store(val, ptr)

    def visit_VarRef(self, node, env):
        if node.name not in env:
            raise ValueError(f"Biến chưa được khai báo: {node.name}")
        ptr = env[node.name]
        return self.builder.load(ptr, name=node.name)

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def visit_Compare(self, node, env):
        left = self.visit(node.left, env)
        right = self.visit(node.right, env)

        op_map = {
            "BANG":        "==",
            "BANG_LON_HON": ">=",
            "BANG_NHO_HON": "<=",
            "KHAC":        "!=",
            "LON_HON":     ">",
            "NHO_HON":     "<",
        }
        llvm_op = op_map[node.op_token]

        if isinstance(left.type, ir.PointerType) or isinstance(right.type, ir.PointerType):
            right = self._match_pointer(right, left.type)
            left = self._match_pointer(left, right.type)
            return self.builder.icmp_unsigned(llvm_op, left, right)

        left, right = self._promote(left, right)
        if left.type == _F64:
            return self.builder.fcmp_ordered(llvm_op, left, right)
        return self.builder.icmp_signed(llvm_op, left, right)

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------

    def _enter_loop(self, env, continue_block, break_block):
        """Push loop targets into *env*; returns the previous values to restore."""
        saved = (env.get("__continue__"), env.get("__break__"))
        env["__continue__"] = continue_block
        env["__break__"] = break_block
        return saved

    def _exit_loop(self, env, saved):
        env["__continue__"], env["__break__"] = saved

    def visit_WhileLoop(self, node, env):
        cond_block = self.builder.append_basic_block("loop_cond")
        body_block = self.builder.append_basic_block("loop_body")
        end_block  = self.builder.append_basic_block("loop_end")

        self.builder.branch(cond_block)

        self.builder.position_at_end(cond_block)
        cond_val = self._to_bool(self.visit(node.condition, env))
        self.builder.cbranch(cond_val, body_block, end_block)

        self.builder.position_at_end(body_block)
        saved = self._enter_loop(env, cond_block, end_block)
        self.visit(node.body, env)
        self._exit_loop(env, saved)
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)

        self.builder.position_at_end(end_block)

    def visit_UntilLoop(self, node, env):
        """đến_khi condition thì ... hết — loops while condition is false."""
        cond_block = self.builder.append_basic_block("until_cond")
        body_block = self.builder.append_basic_block("until_body")
        end_block  = self.builder.append_basic_block("until_end")

        self.builder.branch(cond_block)

        self.builder.position_at_end(cond_block)
        cond_val = self._to_bool(self.visit(node.condition, env))
        not_done = self.builder.not_(cond_val)
        self.builder.cbranch(not_done, body_block, end_block)

        self.builder.position_at_end(body_block)
        saved = self._enter_loop(env, cond_block, end_block)
        self.visit(node.body, env)
        self._exit_loop(env, saved)
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)

        self.builder.position_at_end(end_block)

    def visit_ForRangeLoop(self, node, env):
        """lặp var từ start đến end thì ... hết — counts from start (incl.) to end (excl.)."""
        start_val = self.visit(node.start, env)
        var_ptr = self.builder.alloca(start_val.type, name=node.var)
        self.builder.store(start_val, var_ptr)

        cond_block = self.builder.append_basic_block("for_cond")
        body_block = self.builder.append_basic_block("for_body")
        incr_block = self.builder.append_basic_block("for_incr")
        end_block  = self.builder.append_basic_block("for_end")

        self.builder.branch(cond_block)

        self.builder.position_at_end(cond_block)
        cur = self.builder.load(var_ptr)
        end_val = self.visit(node.end, env)
        cond_val = self.builder.icmp_signed("<", cur, end_val)
        self.builder.cbranch(cond_val, body_block, end_block)

        self.builder.position_at_end(body_block)
        env[node.var] = var_ptr
        saved = self._enter_loop(env, incr_block, end_block)
        self.visit(node.body, env)
        self._exit_loop(env, saved)
        if not self.builder.block.is_terminated:
            self.builder.branch(incr_block)

        self.builder.position_at_end(incr_block)
        cur = self.builder.load(var_ptr)
        nxt = self.builder.add(cur, ir.Constant(cur.type, 1))
        self.builder.store(nxt, var_ptr)
        self.builder.branch(cond_block)

        self.builder.position_at_end(end_block)

    def visit_ForInLoop(self, node, env):
        """lặp var trong array_name thì ... hết — only works on statically-sized
        array literals (the length must have been recorded by visit_VarDecl)."""
        length = env.get("__len__:" + node.array_name)
        if length is None:
            raise ValueError(
                f"Không xác định được độ dài của mảng '{node.array_name}' để lặp 'trong'"
            )
        arr_ptr = self.visit(VarRef(node.array_name), env)

        idx_ptr = self.builder.alloca(_I64, name="for_in_idx")
        self.builder.store(ir.Constant(_I64, 0), idx_ptr)

        cond_block = self.builder.append_basic_block("forin_cond")
        body_block = self.builder.append_basic_block("forin_body")
        incr_block = self.builder.append_basic_block("forin_incr")
        end_block  = self.builder.append_basic_block("forin_end")

        self.builder.branch(cond_block)

        self.builder.position_at_end(cond_block)
        idx = self.builder.load(idx_ptr)
        cond_val = self.builder.icmp_signed("<", idx, ir.Constant(_I64, length))
        self.builder.cbranch(cond_val, body_block, end_block)

        self.builder.position_at_end(body_block)
        idx = self.builder.load(idx_ptr)
        elem_ptr = self.builder.gep(arr_ptr, [idx])
        elem_val = self.builder.load(elem_ptr)
        var_ptr = self.builder.alloca(elem_val.type, name=node.var)
        self.builder.store(elem_val, var_ptr)
        env[node.var] = var_ptr
        saved = self._enter_loop(env, incr_block, end_block)
        self.visit(node.body, env)
        self._exit_loop(env, saved)
        if not self.builder.block.is_terminated:
            self.builder.branch(incr_block)

        self.builder.position_at_end(incr_block)
        idx = self.builder.load(idx_ptr)
        nxt = self.builder.add(idx, ir.Constant(_I64, 1))
        self.builder.store(nxt, idx_ptr)
        self.builder.branch(cond_block)

        self.builder.position_at_end(end_block)

    def visit_BreakStmt(self, node, env):
        target = env.get("__break__")
        if target is None:
            raise ValueError("'ngắt' được dùng ngoài vòng lặp")
        self.builder.branch(target)

    def visit_ContinueStmt(self, node, env):
        target = env.get("__continue__")
        if target is None:
            raise ValueError("'tiếp_theo' được dùng ngoài vòng lặp")
        self.builder.branch(target)

    # ------------------------------------------------------------------
    # Conditional
    # ------------------------------------------------------------------

    def visit_IfStmt(self, node, env):
        cond_val = self._to_bool(self.visit(node.condition, env))

        then_block  = self.builder.append_basic_block("if_then")
        else_block  = self.builder.append_basic_block("if_else") if node.else_body else None
        merge_block = self.builder.append_basic_block("if_merge")

        self.builder.cbranch(cond_val, then_block, else_block if else_block else merge_block)

        self.builder.position_at_end(then_block)
        self.visit(node.then_body, env)
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_block)

        if else_block:
            self.builder.position_at_end(else_block)
            self.visit(node.else_body, env)
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_block)

        self.builder.position_at_end(merge_block)

    def visit_UnlessStmt(self, node, env):
        """nếu_không condition thì ... hết — runs the body when condition is false."""
        cond_val = self._to_bool(self.visit(node.condition, env))
        inverted = self.builder.not_(cond_val)

        then_block  = self.builder.append_basic_block("unless_then")
        merge_block = self.builder.append_basic_block("unless_merge")

        self.builder.cbranch(inverted, then_block, merge_block)

        self.builder.position_at_end(then_block)
        self.visit(node.body, env)
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_block)

        self.builder.position_at_end(merge_block)

    # ------------------------------------------------------------------
    # Functions
    # ------------------------------------------------------------------

    def visit_FuncDef(self, node, env):
        # Functions are typed i64→i64 in this version (no float params/returns yet)
        func_type = ir.FunctionType(_I64, [_I64] * len(node.params))
        func = ir.Function(self.module, func_type, name=node.name)
        env[node.name] = func

        entry_block = func.append_basic_block("entry")
        saved_block = self.builder.block
        self.builder.position_at_end(entry_block)

        local_env = {k: v for k, v in env.items() if isinstance(v, ir.Function)}
        for param_name, arg in zip(node.params, func.args):
            ptr = self.builder.alloca(_I64, name=param_name)
            self.builder.store(arg, ptr)
            local_env[param_name] = ptr

        self.visit(node.body, local_env)

        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(_I64, 0))

        self.builder.position_at_end(saved_block)

    def visit_ReturnStmt(self, node, env):
        val = self.visit(node.expr, env)
        self.builder.ret(val)

    def visit_CallExpr(self, node, env):
        if node.name in self.classes:
            return self._construct_object(node, env)

        if node.name in env:
            func = env[node.name]
        elif node.name in self.module.globals:
            func = self.module.get_global(node.name)
        else:
            raise ValueError(f"Hàm chưa được định nghĩa: {node.name}")

        arg_vals = []
        for arg in node.args:
            val = self.visit(arg, env)
            if isinstance(val.type, ir.PointerType):
                val = self.builder.ptrtoint(val, _I64)
            arg_vals.append(val)
        return self.builder.call(func, arg_vals)

    def _construct_object(self, node, env):
        """Allocate and initialise an instance of a registered class/struct."""
        cls = self.classes[node.name]
        obj_ptr = self.builder.alloca(cls["struct_type"], name=f"{node.name}_obj")

        for i, fname in enumerate(cls["field_order"]):
            default_expr = cls["field_defaults"][fname]
            val = self._to_i64(self.visit(default_expr, env))
            elem_ptr = self.builder.gep(
                obj_ptr, [ir.Constant(_I32, 0), ir.Constant(_I32, i)]
            )
            self.builder.store(val, elem_ptr)

        ctor_owner = cls["methods_owner"].get("khởi_tạo")
        if ctor_owner is not None:
            ctor_func = self.module.get_global(f"{ctor_owner}_khởi_tạo")
            ctor_self_ptr = self._match_pointer(obj_ptr, ctor_func.args[0].type)
            arg_vals = [self._to_i64(self.visit(a, env)) for a in node.args]
            self.builder.call(ctor_func, [ctor_self_ptr] + arg_vals)

        return obj_ptr

    # ------------------------------------------------------------------
    # OOP: classes, structs, interfaces
    #
    # Simplified model: every field is stored as i64 (numeric/bool/pointer
    # values are coerced via ``_to_i64``). Inheritance (``mở_rộng``) merges
    # the parent's fields/methods at compile time; method dispatch is
    # static (resolved from the declared/inferred class of a variable), not
    # a runtime vtable. Objects are stack-allocated (``alloca``) and do not
    # outlive the function that creates them.
    # ------------------------------------------------------------------

    def visit_ClassDef(self, node, env):
        parent = self.classes.get(node.parent) if node.parent else None
        field_order = list(parent["field_order"]) if parent else []
        field_defaults = dict(parent["field_defaults"]) if parent else {}
        methods_owner = dict(parent["methods_owner"]) if parent else {}

        for f in node.fields:
            if f.name not in field_order:
                field_order.append(f.name)
            field_defaults[f.name] = f.expr

        for m in node.methods:
            methods_owner[m.name] = node.name

        struct_type = ir.global_context.get_identified_type(node.name)
        struct_type.set_body(*([_I64] * len(field_order)))

        self.classes[node.name] = {
            "struct_type": struct_type,
            "field_order": field_order,
            "field_defaults": field_defaults,
            "methods_owner": methods_owner,
            "parent": node.parent,
        }

        for m in node.methods:
            self._emit_method(node.name, struct_type, m, env)

    def visit_StructDef(self, node, env):
        struct_type = ir.global_context.get_identified_type(node.name)
        struct_type.set_body(*([_I64] * len(node.fields)))
        self.classes[node.name] = {
            "struct_type": struct_type,
            "field_order": [f.name for f in node.fields],
            "field_defaults": {f.name: f.expr for f in node.fields},
            "methods_owner": {},
            "parent": None,
        }

    def visit_InterfaceDef(self, node, env):
        # Purely declarative: vylang has no "implements" keyword, so this is
        # registered but never checked against a class's methods.
        self.interfaces[node.name] = node.method_names

    def _emit_method(self, class_name, struct_type, node, env):
        self_ptr_type = struct_type.as_pointer()
        func_type = ir.FunctionType(_I64, [self_ptr_type] + [_I64] * len(node.params))
        func = ir.Function(self.module, func_type, name=f"{class_name}_{node.name}")

        entry_block = func.append_basic_block("entry")
        saved_block = self.builder.block
        self.builder.position_at_end(entry_block)

        local_env = {k: v for k, v in env.items() if isinstance(v, ir.Function)}
        self_arg = func.args[0]
        self_ptr_slot = self.builder.alloca(self_ptr_type, name="bản_thân")
        self.builder.store(self_arg, self_ptr_slot)
        local_env["bản_thân"] = self_ptr_slot
        local_env["__class__:bản_thân"] = class_name

        for param_name, arg in zip(node.params, func.args[1:]):
            ptr = self.builder.alloca(_I64, name=param_name)
            self.builder.store(arg, ptr)
            local_env[param_name] = ptr

        self.visit(node.body, local_env)

        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(_I64, 0))

        self.builder.position_at_end(saved_block)

    def _resolve_class(self, obj_name, env):
        class_name = env.get("__class__:" + obj_name)
        if class_name is None:
            raise ValueError(f"Không xác định được lớp của đối tượng: {obj_name}")
        return class_name

    def visit_AttrAccess(self, node, env):
        class_name = self._resolve_class(node.obj_name, env)
        cls = self.classes[class_name]
        idx = cls["field_order"].index(node.field)
        obj_ptr = self.visit(VarRef(node.obj_name), env)
        elem_ptr = self.builder.gep(obj_ptr, [ir.Constant(_I32, 0), ir.Constant(_I32, idx)])
        return self.builder.load(elem_ptr)

    def visit_AttrAssign(self, node, env):
        class_name = self._resolve_class(node.obj_name, env)
        cls = self.classes[class_name]
        idx = cls["field_order"].index(node.field)
        obj_ptr = self.visit(VarRef(node.obj_name), env)
        val = self._to_i64(self.visit(node.expr, env))
        elem_ptr = self.builder.gep(obj_ptr, [ir.Constant(_I32, 0), ir.Constant(_I32, idx)])
        self.builder.store(val, elem_ptr)

    def visit_MethodCall(self, node, env):
        class_name = self._resolve_class(node.obj_name, env)
        cls = self.classes[class_name]
        owner = cls["methods_owner"].get(node.method)
        if owner is None:
            raise ValueError(f"Phương thức chưa được định nghĩa: {class_name}.{node.method}")
        func = self.module.get_global(f"{owner}_{node.method}")
        obj_ptr = self.visit(VarRef(node.obj_name), env)
        obj_ptr = self._match_pointer(obj_ptr, func.args[0].type)
        arg_vals = [self._to_i64(self.visit(a, env)) for a in node.args]
        return self.builder.call(func, [obj_ptr] + arg_vals)

    # ------------------------------------------------------------------
    # Arrays
    # ------------------------------------------------------------------

    def visit_ArrayLiteral(self, node, env):
        size = len(node.elements)
        elem_type = _I64
        if size > 0:
            first_val = self.visit(node.elements[0], env)
            elem_type = first_val.type

        arr_type  = ir.ArrayType(elem_type, size)
        arr_alloc = self.builder.alloca(arr_type, name="array_literal")

        for i, expr in enumerate(node.elements):
            val = self.visit(expr, env)
            elem_ptr = self.builder.gep(arr_alloc, [
                ir.Constant(_I32, 0),
                ir.Constant(_I32, i),
            ])
            self.builder.store(val, elem_ptr)

        return self.builder.gep(arr_alloc, [
            ir.Constant(_I32, 0),
            ir.Constant(_I32, 0),
        ])

    def visit_ArrayIndex(self, node, env):
        arr_val = self.visit(node.array_expr, env)
        if arr_val.type == _I64:
            arr_ptr = self.builder.inttoptr(arr_val, ir.PointerType(_I64))
        else:
            arr_ptr = arr_val
        idx_val  = self.visit(node.index_expr, env)
        elem_ptr = self.builder.gep(arr_ptr, [idx_val])
        return self.builder.load(elem_ptr)

    def visit_ArrayAssign(self, node, env):
        arr_val = self.visit(node.array_expr, env)
        if arr_val.type == _I64:
            arr_ptr = self.builder.inttoptr(arr_val, ir.PointerType(_I64))
        else:
            arr_ptr = arr_val
        idx_val  = self.visit(node.index_expr, env)
        val      = self.visit(node.value_expr, env)
        elem_ptr = self.builder.gep(arr_ptr, [idx_val])
        self.builder.store(val, elem_ptr)

    # ------------------------------------------------------------------
    # Logical operators
    # ------------------------------------------------------------------

    def visit_LogicalAnd(self, node, env):
        l_val = self._to_bool(self.visit(node.left, env))
        r_val = self._to_bool(self.visit(node.right, env))
        return self.builder.and_(l_val, r_val)

    def visit_LogicalOr(self, node, env):
        l_val = self._to_bool(self.visit(node.left, env))
        r_val = self._to_bool(self.visit(node.right, env))
        return self.builder.or_(l_val, r_val)

    def visit_LogicalXor(self, node, env):
        l_val = self._to_bool(self.visit(node.left, env))
        r_val = self._to_bool(self.visit(node.right, env))
        return self.builder.xor(l_val, r_val)

    def visit_IsCompare(self, node, env):
        """là / không_là — treated as value equality (no separate identity model)."""
        left = self.visit(node.left, env)
        right = self.visit(node.right, env)
        op = "!=" if node.negate else "=="

        if isinstance(left.type, ir.PointerType) or isinstance(right.type, ir.PointerType):
            right = self._match_pointer(right, left.type)
            left = self._match_pointer(left, right.type)
            return self.builder.icmp_unsigned(op, left, right)

        left, right = self._promote(left, right)
        if left.type == _F64:
            return self.builder.fcmp_ordered(op, left, right)
        return self.builder.icmp_signed(op, left, right)

    def visit_InCompare(self, node, env):
        """trong / không_trong — membership test over a statically-sized array."""
        length = env.get("__len__:" + node.array_name)
        if length is None:
            raise ValueError(
                f"Không xác định được độ dài của mảng '{node.array_name}' để kiểm tra 'trong'"
            )
        needle = self.visit(node.value, env)
        arr_ptr = self.visit(VarRef(node.array_name), env)

        found_ptr = self.builder.alloca(_I1, name="in_found")
        self.builder.store(ir.Constant(_I1, 0), found_ptr)
        idx_ptr = self.builder.alloca(_I64, name="in_idx")
        self.builder.store(ir.Constant(_I64, 0), idx_ptr)

        cond_block = self.builder.append_basic_block("in_cond")
        body_block = self.builder.append_basic_block("in_body")
        end_block  = self.builder.append_basic_block("in_end")

        self.builder.branch(cond_block)

        self.builder.position_at_end(cond_block)
        idx = self.builder.load(idx_ptr)
        cond_val = self.builder.icmp_signed("<", idx, ir.Constant(_I64, length))
        self.builder.cbranch(cond_val, body_block, end_block)

        self.builder.position_at_end(body_block)
        idx = self.builder.load(idx_ptr)
        elem_ptr = self.builder.gep(arr_ptr, [idx])
        elem_val = self.builder.load(elem_ptr)
        elem_cmp, needle_cmp = self._promote(elem_val, needle)
        if elem_cmp.type == _F64:
            eq = self.builder.fcmp_ordered("==", elem_cmp, needle_cmp)
        else:
            eq = self.builder.icmp_signed("==", elem_cmp, needle_cmp)
        cur_found = self.builder.load(found_ptr)
        self.builder.store(self.builder.or_(cur_found, eq), found_ptr)
        nxt = self.builder.add(idx, ir.Constant(_I64, 1))
        self.builder.store(nxt, idx_ptr)
        self.builder.branch(cond_block)

        self.builder.position_at_end(end_block)
        result = self.builder.load(found_ptr)
        if node.negate:
            result = self.builder.not_(result)
        return result

    # ------------------------------------------------------------------
    # Unary
    # ------------------------------------------------------------------

    def visit_UnaryMinus(self, node, env):
        val = self.visit(node.operand, env)
        if val.type == _F64:
            return self.builder.fneg(val)
        return self.builder.neg(val)

    def visit_UnaryNot(self, node, env):
        val = self._to_bool(self.visit(node.operand, env))
        return self.builder.not_(val)

    # ------------------------------------------------------------------
    # Strings / null
    # ------------------------------------------------------------------

    def visit_StringLiteral(self, node, env):
        return self._string_global(node.value)

    def visit_NullLiteral(self, node, env):
        return ir.Constant(_I8.as_pointer(), None)

    # ------------------------------------------------------------------
    # Exception handling
    #
    # Simplified model: a module-level error flag/value pair stands in for
    # real stack unwinding. ``ném`` sets the flag and branches directly to
    # the innermost enclosing ``thử`` block's catch target (tracked via
    # ``env["__catch__"]``). This only catches throws that occur directly
    # within the try body's own statements/loops/conditionals — a throw
    # from inside a called function will not be caught here, since that
    # function has its own environment without a "__catch__" target.
    # ------------------------------------------------------------------

    def visit_ThrowStmt(self, node, env):
        flag_ptr, value_ptr = self._error_globals()
        val = self._to_i64(self.visit(node.expr, env))
        self.builder.store(ir.Constant(_I1, 1), flag_ptr)
        self.builder.store(val, value_ptr)

        catch_block = env.get("__catch__")
        if catch_block is not None:
            self.builder.branch(catch_block)
            return

        # Uncaught: report and terminate the program.
        exit_fn = self._get_extern("exit", ir.FunctionType(ir.VoidType(), [_I32]))
        self.builder.call(exit_fn, [ir.Constant(_I32, 1)])
        self.builder.unreachable()

    def visit_TryStmt(self, node, env):
        flag_ptr, _ = self._error_globals()
        self.builder.store(ir.Constant(_I1, 0), flag_ptr)

        try_block = self.builder.append_basic_block("try_body")
        catch_block = self.builder.append_basic_block("try_catch")
        finally_block = self.builder.append_basic_block("try_finally") if node.finally_body else None
        end_block = self.builder.append_basic_block("try_end")
        after_catch_target = finally_block if finally_block else end_block

        self.builder.branch(try_block)

        self.builder.position_at_end(try_block)
        saved_catch = env.get("__catch__")
        env["__catch__"] = catch_block
        self.visit(node.try_body, env)
        env["__catch__"] = saved_catch
        if not self.builder.block.is_terminated:
            self.builder.branch(after_catch_target)

        self.builder.position_at_end(catch_block)
        _, value_ptr = self._error_globals()
        err_val = self.builder.load(value_ptr)
        self.builder.store(ir.Constant(_I1, 0), flag_ptr)
        catch_ptr = self.builder.alloca(_I64, name=node.catch_var)
        self.builder.store(err_val, catch_ptr)
        env[node.catch_var] = catch_ptr
        self.visit(node.catch_body, env)
        if not self.builder.block.is_terminated:
            self.builder.branch(after_catch_target)

        if finally_block:
            self.builder.position_at_end(finally_block)
            self.visit(node.finally_body, env)
            if not self.builder.block.is_terminated:
                self.builder.branch(end_block)

        self.builder.position_at_end(end_block)

    # ------------------------------------------------------------------
    # Modules
    # ------------------------------------------------------------------

    def visit_PackageDecl(self, node, env):
        pass

    def visit_ImportStmt(self, node, env):
        # Imports are expanded inline (see vlang.cli) before codegen runs;
        # if one reaches here unexpanded, it's simply a no-op.
        pass

    # ------------------------------------------------------------------
    # Built-in functions
    # ------------------------------------------------------------------

    def visit_ReadLineExpr(self, node, env):
        """đọc_dòng() — reads up to 255 bytes from stdin (fd 0) into a buffer.

        The trailing newline, if any, is kept in the returned string.
        """
        read_fn = self._get_extern(
            "read", ir.FunctionType(_I64, [_I32, _I8.as_pointer(), _I64])
        )
        buf = self.builder.alloca(ir.ArrayType(_I8, 256), name="readline_buf")
        buf_ptr = self.builder.gep(buf, [ir.Constant(_I32, 0), ir.Constant(_I32, 0)])
        n = self.builder.call(read_fn, [ir.Constant(_I32, 0), buf_ptr, ir.Constant(_I64, 255)])
        end_ptr = self.builder.gep(buf_ptr, [n])
        self.builder.store(ir.Constant(_I8, 0), end_ptr)
        return buf_ptr

    def visit_TypeOfExpr(self, node, env):
        """kiểu(expr) — resolves the static LLVM type of *expr* to a type name."""
        val = self.visit(node.expr, env)
        if val.type == _I64:
            name = "số_nguyên"
        elif val.type == _F64:
            name = "số_thực"
        elif val.type == _I1:
            name = "luận_lý"
        elif val.type == _I8.as_pointer():
            name = "chuỗi"
        elif isinstance(val.type, ir.PointerType):
            name = "mảng"
        else:
            name = "không_xác_định"
        return self._string_global(name)
