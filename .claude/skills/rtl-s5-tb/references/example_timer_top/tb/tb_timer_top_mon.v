// ============================================================================
// Component : tb_timer_top_mon - monitor of tb_timer_top
// Observes  : every DUT pin (inputs as really applied, outputs as produced)
// Drives    : s_*_o samples -> u_model (inputs), u_chk (inputs and outputs);
//             s_time_o = time of the sample; s_done_o = 1 in the sample that
//             completes a transfer (psel = penable = pready = 1); s_wait_o =
//             access cycles with pready != 1 before it; s_setup_o = clk count
//             of the setup phase of the transfer on the bus (all observed,
//             not expected)
// Timing    : samples at every falling edge, half a cycle after the stimulus
//             of posedge + #1 and after the outputs have settled; the X->0
//             initialization of clk at time 0 is not an edge (s_vld_o = 0)
// Log       : [OBSERVE] tim_int old -> new on every change of the interrupt
//             output (time of the sample). Transfers are logged by u_chk.
// Ownership : wait_n, int_prev, int_seen, msg (this process only)
// ============================================================================
`timescale 1ns/1ps

module tb_timer_top_mon (
  input  wire        clk_i,
  input  wire [31:0] clk_cnt_i,
  input  wire        rst_n_i,
  input  wire        psel_i,
  input  wire        penable_i,
  input  wire        pwrite_i,
  input  wire [11:0] paddr_i,
  input  wire [31:0] pwdata_i,
  input  wire [3:0]  pstrb_i,
  input  wire        dbg_mode_i,
  input  wire [31:0] prdata_i,
  input  wire        pready_i,
  input  wire        pslverr_i,
  input  wire        tim_int_i,
  output reg  [63:0] s_time_o,
  output reg         s_rst_n_o,
  output reg         s_psel_o,
  output reg         s_penable_o,
  output reg         s_pwrite_o,
  output reg  [11:0] s_paddr_o,
  output reg  [31:0] s_pwdata_o,
  output reg  [3:0]  s_pstrb_o,
  output reg         s_dbg_mode_o,
  output reg  [31:0] s_prdata_o,
  output reg         s_pready_o,
  output reg         s_pslverr_o,
  output reg         s_tim_int_o,
  output reg         s_done_o,
  output reg  [7:0]  s_wait_o,
  output reg  [31:0] s_setup_o,
  output reg         s_vld_o
);

  integer          wait_n;
  reg              int_prev;
  reg              int_seen;
  reg  [8*200-1:0] msg;

  initial begin
    s_vld_o   = 1'b0;
    s_done_o  = 1'b0;
    s_wait_o  = 8'd0;
    s_setup_o = 32'd0;
    wait_n    = 0;
    int_seen  = 1'b0;
  end

  always @(negedge clk_i) begin
    if ($time > 0) begin
      s_vld_o      <= 1'b1;
      s_time_o     <= $time;
      s_rst_n_o    <= rst_n_i;
      s_psel_o     <= psel_i;
      s_penable_o  <= penable_i;
      s_pwrite_o   <= pwrite_i;
      s_paddr_o    <= paddr_i;
      s_pwdata_o   <= pwdata_i;
      s_pstrb_o    <= pstrb_i;
      s_dbg_mode_o <= dbg_mode_i;
      s_prdata_o   <= prdata_i;
      s_pready_o   <= pready_i;
      s_pslverr_o  <= pslverr_i;
      s_tim_int_o  <= tim_int_i;

      // Transfer progress from the pins as really applied
      if (psel_i === 1'b1 && penable_i !== 1'b1) begin
        s_setup_o <= clk_cnt_i;
      end
      if (psel_i === 1'b1 && penable_i === 1'b1) begin
        if (pready_i === 1'b1) begin
          s_done_o <= 1'b1;
          s_wait_o <= wait_n;
          wait_n   = 0;
        end
        else begin
          s_done_o <= 1'b0;
          wait_n   = wait_n + 1;
          s_wait_o <= wait_n;
        end
      end
      else begin
        s_done_o <= 1'b0;
        s_wait_o <= 8'd0;
        wait_n   = 0;
      end

      // Interrupt output changes (first sample only initializes)
      if (int_seen && tim_int_i !== int_prev) begin
        $sformat(msg, "tim_int: %b -> %b", int_prev, tim_int_i);
        tb_timer_top.u_log.info($time, "OBSERVE", msg);
      end
      int_prev = tim_int_i;
      int_seen = 1'b1;
    end
  end

endmodule
