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
        else:
            gv = self._fmt_global("fstr", "%i\n\0")

        fmt_arg = self.builder.bitcast(gv, voidptr_ty)
        self.builder.call(self.printf, [fmt_arg, value])

    def visit_Program(self, node, env):
        for stmt in node.statements:
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

    def visit_VarAssign(self, node, env):
        if node.name not in env:
            raise ValueError(f"Biến chưa được khai báo: {node.name}")
        ptr = env[node.name]
        val = self.visit(node.expr, env)
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
        left, right = self._promote(left, right)

        op_map = {
            "BANG":        "==",
            "BANG_LON_HON": ">=",
            "BANG_NHO_HON": "<=",
            "KHAC":        "!=",
            "LON_HON":     ">",
            "NHO_HON":     "<",
        }
        llvm_op = op_map[node.op_token]
        if left.type == _F64:
            return self.builder.fcmp_ordered(llvm_op, left, right)
        return self.builder.icmp_signed(llvm_op, left, right)

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------

    def visit_WhileLoop(self, node, env):
        cond_block = self.builder.append_basic_block("loop_cond")
        body_block = self.builder.append_basic_block("loop_body")
        end_block  = self.builder.append_basic_block("loop_end")

        self.builder.branch(cond_block)

        self.builder.position_at_end(cond_block)
        cond_val = self._to_bool(self.visit(node.condition, env))
        self.builder.cbranch(cond_val, body_block, end_block)

        self.builder.position_at_end(body_block)
        self.visit(node.body, env)
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)

        self.builder.position_at_end(end_block)

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

    # ------------------------------------------------------------------
    # Unary
    # ------------------------------------------------------------------

    def visit_UnaryMinus(self, node, env):
        val = self.visit(node.operand, env)
        if val.type == _F64:
            return self.builder.fneg(val)
        return self.builder.neg(val)
