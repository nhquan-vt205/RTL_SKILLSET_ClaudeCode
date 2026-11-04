// Testbench file list, paths relative to sim/. Lines containing // are comments.
// Component modules tb/tb_<m>_<role>.v of every testbench, grouped by branch
// like rtl.f ("// --- <b> ---" + one file per line, S5 adds them), then the
// testbench top of the selected test (TB_NAME is exported by the Makefile).
// Example:
// --- my_module ---
// ../tb/tb_my_module_drv.v

../tb/${TB_NAME}.v
