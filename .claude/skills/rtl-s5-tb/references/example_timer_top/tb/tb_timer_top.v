// ============================================================================
// Testbench : tb_timer_top - self-checking direct integration testbench of
//             timer_top (apb_slave, register, cnt_ctrl, counter, interrupt)
// Spec      : doc/spec/architecture/timer_top_spec.md, apb_slave_spec.md,
//             cnt_ctrl_spec.md, doc/spec/register_file/register_map.md
// Vplan     : doc/vplan/timer_top_vplan.md (scenarios and grouping only;
//             every expected value comes from u_model)
// Test cases: tc/TC_TIMER_TOP_<NNN>.v, one per VPLAN Item, copied to
//             sim/run_test.v by "make build" and included in section 9
// Components (tb/, listed in sim/tb.f before this file):
//   u_clk_rst tb_timer_top_clk_rst clock/reset generator -> clk, rst_n, clk_cnt
//   u_drv     tb_timer_top_drv     APB master + dbg_mode -> tim_p*, dbg_mode
//   u_mon     tb_timer_top_mon     monitor               -> s_* samples, s_time, s_done
//   u_model   tb_timer_top_model   golden reference model-> exp_*
//   u_chk     tb_timer_top_chk     checker               -> u_log.check / info
//   u_log     tb_timer_top_log     logger, owns pass_count / fail_count
// Log       : one line per stimulus applied (APB transfer at its completion,
//             [DRIVE], [RESET], [WAIT]) and per check; deviations only for the
//             per-sample watch. No model explanation line.
// Dataflow  : tc -> u_drv -> u_dut -> u_mon -> u_model -> u_chk -> u_log
//                                     u_mon --------------> u_chk
//             u_dut tim_pready -> u_drv (end of transfer only; its timing is
//             checked by u_chk against u_model)
// Black box : stimulus only on timer_top ports, observation only on its
//             outputs; no force/deposit, no internal signal of u_dut is read.
// ============================================================================
`timescale 1ns/1ps

module tb_timer_top;

  // ============================================================
  // 1. Declaration
  // ============================================================
  parameter CLK_PERIOD   = 20;
  parameter RESET_CYCLES = 2;
  parameter TIMEOUT_NS   = 200000;
  // Checker sample point: falling edge + CHK_DLY
  parameter CHK_DLY      = 1;
  // Longest APB access the driver waits for (spec: one wait state)
  parameter MAX_WAIT     = 8;
  // Log columns: time digits, clk-count digits, tag width, expected/actual
  // width
  parameter TIME_W       = 8;
  parameter CLK_W        = 6;
  parameter TAG_W        = 17;
  parameter VAL_W        = 10;

  // Register offsets (register map)
  parameter ADDR_TCR   = 12'h000;
  parameter ADDR_TDR0  = 12'h004;
  parameter ADDR_TDR1  = 12'h008;
  parameter ADDR_TCMP0 = 12'h00C;
  parameter ADDR_TCMP1 = 12'h010;
  parameter ADDR_TIER  = 12'h014;
  parameter ADDR_TISR  = 12'h018;
  parameter ADDR_THCSR = 12'h01C;

  wire             clk;           // u_clk_rst
  wire             rst_n;         // u_clk_rst
  wire [31:0]      clk_cnt;       // u_clk_rst
  wire             tim_psel;      // u_drv
  wire             tim_penable;   // u_drv
  wire             tim_pwrite;    // u_drv
  wire [11:0]      tim_paddr;     // u_drv
  wire [31:0]      tim_pwdata;    // u_drv
  wire [3:0]       tim_pstrb;     // u_drv
  wire             dbg_mode;      // u_drv
  wire [31:0]      tim_prdata;    // u_dut
  wire             tim_pready;    // u_dut
  wire             tim_pslverr;   // u_dut
  wire             tim_int;       // u_dut
  wire [63:0]      s_time;        // u_mon
  wire             s_rst_n;       // u_mon
  wire             s_psel;        // u_mon
  wire             s_penable;     // u_mon
  wire             s_pwrite;      // u_mon
  wire [11:0]      s_paddr;       // u_mon
  wire [31:0]      s_pwdata;      // u_mon
  wire [3:0]       s_pstrb;       // u_mon
  wire             s_dbg_mode;    // u_mon
  wire [31:0]      s_prdata;      // u_mon
  wire             s_pready;      // u_mon
  wire             s_pslverr;     // u_mon
  wire             s_tim_int;     // u_mon
  wire             s_done;        // u_mon
  wire [7:0]       s_wait;        // u_mon
  wire [31:0]      s_setup;       // u_mon
  wire             s_vld;         // u_mon
  wire [31:0]      exp_prdata;    // u_model
  wire             exp_pready;    // u_model
  wire             exp_pslverr;   // u_model
  wire             exp_tim_int;   // u_model

  // Variables of the sequence tasks
  reg  [8*256-1:0] msg;

  // ============================================================
  // 2. DUT Instance
  // ============================================================
  timer_top u_dut (
    .sys_clk     (clk),
    .sys_rst_n   (rst_n),
    .tim_psel    (tim_psel),
    .tim_pwrite  (tim_pwrite),
    .tim_penable (tim_penable),
    .tim_paddr   (tim_paddr),
    .tim_pwdata  (tim_pwdata),
    .tim_pstrb   (tim_pstrb),
    .tim_prdata  (tim_prdata),
    .tim_pready  (tim_pready),
    .tim_pslverr (tim_pslverr),
    .tim_int     (tim_int),
    .dbg_mode    (dbg_mode)
  );

  // ============================================================
  // 3. Clock Generation
  // ============================================================
  tb_timer_top_clk_rst #(
    .CLK_PERIOD (CLK_PERIOD)
  ) u_clk_rst (
    .clk_o   (clk),
    .rst_n_o (rst_n),
    .clk_cnt_o (clk_cnt)
  );

  // ============================================================
  // 4. Init Reset
  // ============================================================
  // Bus idle and dbg_mode = 0 now, asynchronous reset for RESET_CYCLES
  // edges, release at posedge + #1 (outputs watched against the model in
  // every sample). DUT and model reset (model follows rst_n); clk_cnt and
  // the log counters are kept
  task reset_dut;
    begin
      u_drv.drive_idle;
      u_clk_rst.apply_reset(RESET_CYCLES);
      u_chk.sync;
    end
  endtask

  // ============================================================
  // 5. Golden Reference Model
  // ============================================================
  tb_timer_top_model u_model (
    .clk_i         (clk),
    .rst_n_i       (rst_n),
    .s_psel_i      (s_psel),
    .s_penable_i   (s_penable),
    .s_pwrite_i    (s_pwrite),
    .s_paddr_i     (s_paddr),
    .s_pwdata_i    (s_pwdata),
    .s_pstrb_i     (s_pstrb),
    .s_dbg_mode_i  (s_dbg_mode),
    .exp_prdata_o  (exp_prdata),
    .exp_pready_o  (exp_pready),
    .exp_pslverr_o (exp_pslverr),
    .exp_tim_int_o (exp_tim_int)
  );

  // ============================================================
  // 6. Checker
  // ============================================================
  // Monitor -> checker (with model) -> logger
  tb_timer_top_mon u_mon (
    .clk_i        (clk),
    .clk_cnt_i    (clk_cnt),
    .rst_n_i      (rst_n),
    .psel_i       (tim_psel),
    .penable_i    (tim_penable),
    .pwrite_i     (tim_pwrite),
    .paddr_i      (tim_paddr),
    .pwdata_i     (tim_pwdata),
    .pstrb_i      (tim_pstrb),
    .dbg_mode_i   (dbg_mode),
    .prdata_i     (tim_prdata),
    .pready_i     (tim_pready),
    .pslverr_i    (tim_pslverr),
    .tim_int_i    (tim_int),
    .s_time_o     (s_time),
    .s_rst_n_o    (s_rst_n),
    .s_psel_o     (s_psel),
    .s_penable_o  (s_penable),
    .s_pwrite_o   (s_pwrite),
    .s_paddr_o    (s_paddr),
    .s_pwdata_o   (s_pwdata),
    .s_pstrb_o    (s_pstrb),
    .s_dbg_mode_o (s_dbg_mode),
    .s_prdata_o   (s_prdata),
    .s_pready_o   (s_pready),
    .s_pslverr_o  (s_pslverr),
    .s_tim_int_o  (s_tim_int),
    .s_done_o     (s_done),
    .s_wait_o     (s_wait),
    .s_setup_o    (s_setup),
    .s_vld_o      (s_vld)
  );

  tb_timer_top_chk #(
    .CHK_DLY (CHK_DLY)
  ) u_chk (
    .clk_i         (clk),
    .clk_cnt_i     (clk_cnt),
    .s_time_i      (s_time),
    .s_rst_n_i     (s_rst_n),
    .s_psel_i      (s_psel),
    .s_penable_i   (s_penable),
    .s_pwrite_i    (s_pwrite),
    .s_paddr_i     (s_paddr),
    .s_pwdata_i    (s_pwdata),
    .s_pstrb_i     (s_pstrb),
    .s_prdata_i    (s_prdata),
    .s_pready_i    (s_pready),
    .s_pslverr_i   (s_pslverr),
    .s_tim_int_i   (s_tim_int),
    .s_done_i      (s_done),
    .s_wait_i      (s_wait),
    .s_setup_i     (s_setup),
    .s_vld_i       (s_vld),
    .exp_prdata_i  (exp_prdata),
    .exp_pready_i  (exp_pready),
    .exp_pslverr_i (exp_pslverr),
    .exp_tim_int_i (exp_tim_int)
  );

  tb_timer_top_log #(
    .TIME_W (TIME_W),
    .CLK_W  (CLK_W),
    .TAG_W  (TAG_W),
    .VAL_W  (VAL_W)
  ) u_log (
    .clk_cnt_i (clk_cnt)
  );

  // ============================================================
  // 7. Helper Functions
  // ============================================================
  // Register-map presentation for the log (used by u_drv, u_chk); no
  // checking logic

  // Register name of an APB address (word decode paddr[11:2])
  function [8*8-1:0] reg_name;
    input [11:0] addr;
    begin
      case (addr[11:2])
        10'h000: reg_name = "TCR";
        10'h001: reg_name = "TDR0";
        10'h002: reg_name = "TDR1";
        10'h003: reg_name = "TCMP0";
        10'h004: reg_name = "TCMP1";
        10'h005: reg_name = "TIER";
        10'h006: reg_name = "TISR";
        10'h007: reg_name = "THCSR";
        default: reg_name = "RSVD";
      endcase
    end
  endfunction

  // Names of the register fields covered by the bit mask m (note of a
  // register read FAIL), separated by spaces
  function [8*80-1:0] field_names;
    input [11:0] addr;
    input [31:0] m;
    reg   [8*80-1:0] r;
    reg   [8*80-1:0] t;
    begin
      r = "";
      case (addr[11:2])
        10'h000: begin
          if (m[0]) begin
            $sformat(t, "%0s TIM_EN", r);
            r = t;
          end
          if (m[1]) begin
            $sformat(t, "%0s DIV_EN", r);
            r = t;
          end
          if (|m[11:8]) begin
            $sformat(t, "%0s DIV_VAL", r);
            r = t;
          end
          if (|{m[31:12], m[7:2]}) begin
            $sformat(t, "%0s reserved", r);
            r = t;
          end
        end
        10'h007: begin
          if (m[0]) begin
            $sformat(t, "%0s HALT_REQ", r);
            r = t;
          end
          if (m[1]) begin
            $sformat(t, "%0s HALT_ACK", r);
            r = t;
          end
          if (|m[31:2]) begin
            $sformat(t, "%0s reserved", r);
            r = t;
          end
        end
        10'h005: begin
          r = m[0] ? " INT_EN" : " reserved";
        end
        10'h006: begin
          r = m[0] ? " INT_ST" : " reserved";
        end
        10'h003, 10'h004: begin
          r = " compare value";
        end
        default: begin
          r = " reserved (RAZ)";
        end
      endcase
      field_names = r & ~({8'hFF, {79{8'h00}}} >> (8 * (80 - str_len80(r))));
    end
  endfunction

  // Number of characters of a string
  function integer str_len80;
    input [8*80-1:0] s;
    integer          k;
    begin
      str_len80 = 0;
      for (k = 0; k < 80; k = k + 1) begin
        if (s[8*k +: 8] != 8'h0) begin
          str_len80 = k + 1;
        end
      end
    end
  endfunction

  // ============================================================
  // 8. Tasks
  // ============================================================
  // Stimulus driver, called by the tasks below and reset_dut
  tb_timer_top_drv #(
    .MAX_WAIT (MAX_WAIT)
  ) u_drv (
    .clk_i      (clk),
    .clk_cnt_i  (clk_cnt),
    .pready_i   (tim_pready),
    .psel_o     (tim_psel),
    .penable_o  (tim_penable),
    .pwrite_o   (tim_pwrite),
    .paddr_o    (tim_paddr),
    .pwdata_o   (tim_pwdata),
    .pstrb_o    (tim_pstrb),
    .dbg_mode_o (dbg_mode)
  );

  // Sequence tasks of the test cases: stimulus only, no expected value.
  // Each returns after u_chk has checked the last sample (u_chk.sync), so
  // a branch header printed next owns only the following checks.

  // APB write; u_chk checks the response against the model at completion
  task apb_write;
    input [11:0] addr;
    input [31:0] wdata;
    input [3:0]  strb;
    begin
      u_drv.apb_write(addr, wdata, strb);
      u_chk.sync;
    end
  endtask

  // APB read; u_chk checks response and read data against the model
  task apb_read;
    input [11:0] addr;
    begin
      u_drv.apb_read(addr);
      u_chk.sync;
    end
  endtask

  // dbg_mode from the next drive point (posedge + #1, bus idle that cycle)
  task set_dbg_mode;
    input v;
    begin
      u_drv.set_dbg_mode(v);
      u_chk.sync;
    end
  endtask

  // n idle cycles, one [WAIT] line (every sample still checked)
  task wait_cycles;
    input integer n;
    begin
      u_drv.idle(n);
      u_chk.sync;
    end
  endtask

  // Once per Item, before its first header: counters, log context
  task init_test;
    input [8*24-1:0]  id;
    input [8*200-1:0] objective;
    begin
      u_log.init;
      $sformat(msg, "%0s: %0s", id, objective);
      u_log.banner(msg);
      u_log.banner("DUT timer_top, public ports only (APB, dbg_mode); spec doc/spec/architecture/{timer_top,apb_slave,cnt_ctrl}_spec.md, doc/spec/register_file/register_map.md");
      $sformat(msg, "Time: t in ns; clk = sys_clk rising edges since time 0 (%0d ns period, never reset); inputs applied at rising edge + 1 ns, outputs sampled at the falling edge; APB line at completion, setup at clk - 2",
               CLK_PERIOD);
      u_log.banner(msg);
      u_log.banner("Checks: expected from the golden model tb_timer_top_model; outputs compared at every falling edge, only deviations printed; APB WRITE ... OK = no error response (not a data check)");
    end
  endtask

  // Once per Item: summary, Test_result, end of simulation
  task end_test;
    begin
      u_log.summary;
      $finish;
    end
  endtask

  // ============================================================
  // 9. Main Program Body
  // ============================================================
  // Test sequence of the selected Item (tc/<ID>.v)
`include "run_test.v"

  initial begin
    #(TIMEOUT_NS);
    $sformat(msg, "simulation exceeded %0d ns", TIMEOUT_NS);
    u_log.error_msg($time, "TIMEOUT", msg);
    end_test;
  end

endmodule
