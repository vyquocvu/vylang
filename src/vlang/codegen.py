"""
LLVM IR code generator for the vlang compiler.

Wraps llvmlite to:
  - Configure the LLVM target and execution engine.
  - Declare the C ``printf`` function for use by Print nodes.
  - Compile the module IR and optionally save it to disk.
"""

from pathlib import Path

from llvmlite import ir, binding


class CodeGen:
    """Sets up the LLVM module, builder, and execution engine.

    Usage::

        cg = CodeGen()
        # ... build AST nodes using cg.module, cg.builder, cg.printf ...
        cg.create_ir()
        cg.save_ir("output.ll")
    """

    def __init__(self) -> None:
        self.binding = binding
        self.binding.initialize()
        self.binding.initialize_native_target()
        self.binding.initialize_native_asmprinter()
        self._config_llvm()
        self._create_execution_engine()
        self._declare_print_function()

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _config_llvm(self) -> None:
        """Create the root LLVM module and a ``main`` function builder."""
        self.module = ir.Module(name=Path(__file__).stem)
        self.module.triple = self.binding.get_default_triple()

        func_type = ir.FunctionType(ir.VoidType(), [], False)
        base_func = ir.Function(self.module, func_type, name="main")
        block = base_func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)

    def _create_execution_engine(self) -> None:
        """Create an MCJIT execution engine for the host CPU."""
        target = self.binding.Target.from_default_triple()
        target_machine = target.create_target_machine()
        backing_mod = binding.parse_assembly("")
        self.engine = binding.create_mcjit_compiler(backing_mod, target_machine)

    def _declare_print_function(self) -> None:
        """Forward-declare the C ``printf`` function in the module."""
        voidptr_ty = ir.IntType(8).as_pointer()
        printf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
        self.printf = ir.Function(self.module, printf_ty, name="printf")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, ast) -> None:
        """Emit LLVM IR for *ast* into this module via ``CodeGenVisitor``."""
        from vlang.visitor import CodeGenVisitor

        visitor = CodeGenVisitor(self.module, self.builder, self.printf)
        visitor.generate(ast)

    def _compile_ir(self) -> binding.ModuleRef:
        """Finalise the IR, verify it, and load it into the engine."""
        self.builder.ret_void()
        llvm_ir = str(self.module)
        mod = self.binding.parse_assembly(llvm_ir)
        mod.verify()
        self.engine.add_module(mod)
        self.engine.finalize_object()
        self.engine.run_static_constructors()
        return mod

    def create_ir(self) -> None:
        """Compile the accumulated IR. Call after all AST nodes are evaluated."""
        self._compile_ir()

    def save_ir(self, filename: str) -> None:
        """Write the LLVM IR text to *filename* (e.g. ``output.ll``)."""
        with open(filename, "w", encoding="utf-8") as fh:
            fh.write(str(self.module))

    def jit_run(self) -> None:
        """JIT-compile and execute ``main()`` in-process via MCJIT + ctypes.

        printf calls inside the program write directly to the process stdout,
        so REPL output appears immediately without subprocess overhead.
        """
        import ctypes

        mod = self._compile_ir()
        func_ptr = self.engine.get_function_address("main")
        cfunc = ctypes.CFUNCTYPE(None)(func_ptr)
        cfunc()
