// ============================================================================
// Component : tb_timer_top_clk_rst - clock/reset generator of tb_timer_top
// Drives    : clk_o, rst_n_o, clk_cnt_o (only driver of these nets)
// Timing    : first rising edge at CLK_PERIOD / 2. clk_cnt_o = number of
//             rising edges since time 0: set to 0 once, +1 at every rising
//             edge (nonblocking: a process woken by the same edge still
//             reads the old count), never reset (DUT reset, init_test and
//             branch changes keep it). rst_n_o is the active-low
//             asynchronous reset of the spec: asserted immediately,
//             released at posedge + #1.
// Log       : [RESET] at assert and at release (tb_timer_top.u_log.info)
// Called by : tb_timer_top (reset_dut)
// ============================================================================
`timescale 1ns/1ps

module tb_timer_top_clk_rst #(
  parameter CLK_PERIOD = 20
) (
  output reg        clk_o,
  output reg        rst_n_o,
  output reg [31:0] clk_cnt_o
);

  reg [8*200-1:0] msg;

  initial begin
    clk_o     = 1'b0;
    rst_n_o   = 1'b0;
    clk_cnt_o = 32'd0;
  end

  always #(CLK_PERIOD / 2) clk_o = ~clk_o;

  always @(posedge clk_o) begin
    clk_cnt_o <= clk_cnt_o + 32'd1;
  end

  // Assert now, hold n rising edges, release at posedge + #1
  task apply_reset;
    input integer n;
    begin
      rst_n_o = 1'b0;
      $sformat(msg, "sys_rst_n = 0 (asserted for %0d rising edges)", n);
      tb_timer_top.u_log.info($time, "RESET", msg);
      repeat (n) begin
        @(posedge clk_o);
      end
      #1;
      rst_n_o = 1'b1;
      tb_timer_top.u_log.info($time, "RESET", "sys_rst_n = 1 (released)");
    end
  endtask

endmodule
