// ============================================================================
// Component : tb_timer_top_drv - APB master and dbg_mode driver of
//             tb_timer_top
// Drives    : psel_o, penable_o, pwrite_o, paddr_o, pwdata_o, pstrb_o,
//             dbg_mode_o -> DUT inputs (only driver of these nets)
// Receives  : clk_i, clk_cnt_i, pready_i (APB handshake, read at the falling
//             edge only to know when the transfer ends - its timing is
//             checked against the model by u_chk)
// Timing    : every change at posedge + #1. Each task covers whole cycles
//             and returns at the falling edge of its last cycle; the next
//             call drives at the next posedge + #1 (back-to-back transfers
//             keep tim_psel = 1, no idle cycle is inserted). Transfer: setup
//             (psel 1, penable 0), then access (penable 1) until
//             pready_i = 1, at most MAX_WAIT wait cycles ([TIMEOUT],
//             transfer abandoned). A task that is not a transfer (idle,
//             set_dbg_mode) drives the bus idle.
// Log       : only inputs outside the bus, at the time they are applied:
//             [DRIVE] dbg_mode old -> new (only on a real change), [WAIT]
//             n cycles; [TIMEOUT] of an abandoned transfer. An APB transfer
//             is logged once, at its completion, by u_chk.
// Called by : sequence tasks and reset_dut of tb_timer_top
// Ownership : nwait, setup_c, k, msg (calls never overlap: one test
//             sequence process)
// ============================================================================
`timescale 1ns/1ps

module tb_timer_top_drv #(
  parameter MAX_WAIT = 8
) (
  input  wire        clk_i,
  input  wire [31:0] clk_cnt_i,
  input  wire        pready_i,
  output reg         psel_o,
  output reg         penable_o,
  output reg         pwrite_o,
  output reg  [11:0] paddr_o,
  output reg  [31:0] pwdata_o,
  output reg  [3:0]  pstrb_o,
  output reg         dbg_mode_o
);

  integer          nwait;
  integer          setup_c;
  integer          k;
  reg  [8*200-1:0] msg;

  // Bus idle values, no edge (internal)
  task bus_idle;
    begin
      psel_o    = 1'b0;
      penable_o = 1'b0;
      pwrite_o  = 1'b0;
      paddr_o   = 12'h0;
      pwdata_o  = 32'h0;
      pstrb_o   = 4'h0;
    end
  endtask

  // dbg_mode change, logged only when the value really changes
  task drive_dbg;
    input v;
    begin
      if (dbg_mode_o !== v && (dbg_mode_o === 1'b0 || dbg_mode_o === 1'b1)) begin
        $sformat(msg, "dbg_mode: %b -> %b", dbg_mode_o, v);
        tb_timer_top.u_log.info($time, "DRIVE", msg);
      end
      dbg_mode_o = v;
    end
  endtask

  // Idle bus and dbg_mode = 0 without waiting for an edge (reset only)
  task drive_idle;
    begin
      bus_idle;
      drive_dbg(1'b0);
    end
  endtask

  // One APB transfer; returns at the falling edge of the last access cycle
  task apb_xfer;
    input        wr;
    input [11:0] addr;
    input [31:0] wdata;
    input [3:0]  strb;
    begin
      // Setup phase
      @(posedge clk_i);
      #1;
      setup_c   = clk_cnt_i;
      psel_o    = 1'b1;
      penable_o = 1'b0;
      pwrite_o  = wr;
      paddr_o   = addr;
      pwdata_o  = wr ? wdata : 32'h0;
      pstrb_o   = wr ? strb : 4'h0;

      // Access phase, held until pready
      @(posedge clk_i);
      #1;
      penable_o = 1'b1;
      nwait = 0;
      @(negedge clk_i);
      while (pready_i !== 1'b1 && nwait < MAX_WAIT) begin
        nwait = nwait + 1;
        @(posedge clk_i);
        #1;
        @(negedge clk_i);
      end
      if (pready_i !== 1'b1) begin
        $sformat(msg, "APB %0s %0s: no tim_pready = 1 in %0d access cycles (setup clk=%0d); transfer abandoned, bus idle",
                 wr ? "WRITE" : "READ", tb_timer_top.reg_name(addr), MAX_WAIT + 1, setup_c);
        tb_timer_top.u_log.error_msg($time, "TIMEOUT", msg);
        @(posedge clk_i);
        #1;
        bus_idle;
        @(negedge clk_i);
      end
    end
  endtask

  task apb_write;
    input [11:0] addr;
    input [31:0] wdata;
    input [3:0]  strb;
    begin
      apb_xfer(1'b1, addr, wdata, strb);
    end
  endtask

  task apb_read;
    input [11:0] addr;
    begin
      apb_xfer(1'b0, addr, 32'h0, 4'h0);
    end
  endtask

  // n idle cycles (bus idle, dbg_mode kept), one [WAIT] line
  task idle;
    input integer n;
    begin
      for (k = 0; k < n; k = k + 1) begin
        @(posedge clk_i);
        #1;
        bus_idle;
        if (k == 0) begin
          $sformat(msg, "%0d cycles, bus idle (clk=%0d..%0d)", n, clk_cnt_i, clk_cnt_i + n - 1);
          tb_timer_top.u_log.info($time, "WAIT", msg);
        end
        @(negedge clk_i);
      end
    end
  endtask

  // dbg_mode from the next drive point (posedge + #1); that cycle has the
  // bus idle, the next task drives at the following posedge + #1
  task set_dbg_mode;
    input v;
    begin
      @(posedge clk_i);
      #1;
      bus_idle;
      drive_dbg(v);
      @(negedge clk_i);
    end
  endtask

endmodule
