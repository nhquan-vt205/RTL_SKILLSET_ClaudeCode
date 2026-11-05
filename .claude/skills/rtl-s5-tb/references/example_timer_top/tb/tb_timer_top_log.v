// ============================================================================
// Component : tb_timer_top_log - logger / result collector of tb_timer_top
// Owns      : pass_count, fail_count (only this module changes them) and the
//             branch context
// Receives  : clk_cnt_i (rising edges since time 0, from u_clk_rst)
// Called by : test case (item / sub1 / sub2 / goal), tb_timer_top (init,
//             banner, error_msg, summary), u_clk_rst / u_drv / u_mon (info),
//             u_chk (check, info); every component formats values with
//             fmt_hex / fmt_bin / fmt_dec / fmt_cnt / fmt_sdec / fmt_bit
// Log       : [TEST] context, [ITEM] / [SUBITEM1] / [SUBITEM2] / [GOAL],
//             event line  "<prefix> [<TAG>] <text>"                 not counted
//             check line  "<prefix> [<TAG>] <text> expected: <e> actual: <a>
//                          PASS|FAIL [(<note>)]"                    one count
//             error line  "<prefix> [TIMEOUT|PROTOCOL ERROR|LOG ERROR] <text>"
//                                                                   one FAIL
//             [SUMMARY] PASS=<n> FAIL=<n>, Test_result (check_sim_log.py,
//             sim/report.csh)
// Prefix    : [t=<ns> ns clk=<n>]; t is the time of the event passed by the
//             caller (stimulus applied / output sampled), n the rising-edge
//             count at that time (unchanged between the event and the print:
//             prints happen before the next rising edge)
// Tasks have no timing control: each call prints its line atomically.
// ============================================================================
`timescale 1ns/1ps

module tb_timer_top_log #(
  parameter TIME_W = 8,
  parameter CLK_W  = 6,
  parameter TAG_W  = 18,
  parameter VAL_W  = 10
) (
  input wire [31:0] clk_cnt_i
);

  integer          pass_count;
  integer          fail_count;
  integer          level;
  reg  [8*64-1:0]  cur_item;
  reg  [8*64-1:0]  cur_sub1;
  reg  [8*80-1:0]  tg;
  reg  [8*200-1:0] tx;
  reg  [8*128-1:0] nt;

  // Once per Item (init_test); a DUT reset does not call it
  task init;
    begin
      pass_count = 0;
      fail_count = 0;
      level      = 0;
      cur_item   = 0;
      cur_sub1   = 0;
    end
  endtask

  // Context line of the log header (no timestamp)
  task banner;
    input [8*256-1:0] text;
    begin
      $display("[TEST] %0s", text);
    end
  endtask

  // Branch headers; a new parent clears the context of its children
  task item;
    input [8*64-1:0] name;
    begin
      cur_item = name;
      cur_sub1 = 0;
      level    = 1;
      $display("[ITEM] %0s", name);
    end
  endtask

  task sub1;
    input [8*64-1:0] name;
    begin
      if (cur_item == 0) begin
        error_msg($time, "LOG ERROR", "[SUBITEM1] without [ITEM]");
      end
      cur_sub1 = name;
      level    = 2;
      $display("  [SUBITEM1] %0s", name);
    end
  endtask

  task sub2;
    input [8*64-1:0] name;
    begin
      if (cur_sub1 == 0) begin
        error_msg($time, "LOG ERROR", "[SUBITEM2] without [SUBITEM1]");
      end
      level = 3;
      $display("    [SUBITEM2] %0s", name);
    end
  endtask

  // One short objective line right below the open header
  task goal;
    input [8*200-1:0] text;
    begin
      case (level)
        1:       $display("  [GOAL] %0s", text);
        2:       $display("    [GOAL] %0s", text);
        default: $display("      [GOAL] %0s", text);
      endcase
    end
  endtask

  // Event line (stimulus applied, observation, diagnosis). Never counted.
  task info;
    input [63:0]      t;
    input [8*64-1:0]  tag;
    input [8*200-1:0] text;
    begin
      $sformat(tg, "[%0s]", tag);
      $display("%0s %0s %0s", prefix(t), pad_right(tg, TAG_W), text);
    end
  endtask

  // Check line: exactly one counter per call; text may be empty; w = width
  // of the expected / actual fields (VAL_W for aligned columns, 0 = none);
  // note (may be empty) = short direct context of a FAIL, printed after the
  // verdict in parentheses - the deviation stays on one line
  task check;
    input [63:0]      t;
    input [8*64-1:0]  tag;
    input [8*200-1:0] text;
    input             pass;
    input [8*80-1:0]  exp_s;
    input [8*80-1:0]  act_s;
    input integer     w;
    input [8*120-1:0] note;
    begin
      if (pass === 1'b1) begin
        pass_count = pass_count + 1;
      end
      else begin
        fail_count = fail_count + 1;
      end
      $sformat(tg, "[%0s]", tag);
      if (text == 0) begin
        tx = "";
      end
      else begin
        $sformat(tx, "%0s ", text);
      end
      if (note == 0) begin
        nt = "";
      end
      else begin
        $sformat(nt, " (%0s)", note);
      end
      $display("%0s %0s %0sexpected: %0s actual: %0s %0s%0s", prefix(t), pad_right(tg, TAG_W), tx,
               pad_left(exp_s, w), pad_left(act_s, w), (pass === 1'b1) ? "PASS" : "FAIL", nt);
    end
  endtask

  // Failure without a comparison: kind = TIMEOUT, PROTOCOL ERROR, LOG ERROR
  task error_msg;
    input [63:0]      t;
    input [8*64-1:0]  kind;
    input [8*200-1:0] text;
    begin
      fail_count = fail_count + 1;
      $sformat(tg, "[%0s]", kind);
      $display("%0s %0s %0s", prefix(t), pad_right(tg, TAG_W), text);
    end
  endtask

  // Summary and overall result (read by sim/report.csh)
  task summary;
    begin
      $display("[SUMMARY] PASS=%0d FAIL=%0d", pass_count, fail_count);
      if (fail_count == 0 && pass_count > 0) begin
        $display("Test_result: PASSED");
      end
      else begin
        $display("Test_result: FAILED");
      end
    end
  endtask

  // ------------------------------------------------------------------
  // Line prefix: event time and rising-edge count
  // ------------------------------------------------------------------
  function [8*80-1:0] prefix;
    input [63:0] t;
    reg   [8*80-1:0] ts;
    reg   [8*80-1:0] cs;
    reg   [8*80-1:0] r;
    begin
      $sformat(ts, "%0d", t);
      // Before the first rising edge the count is 0 (clk_cnt may still be X
      // at time 0, depending on the order of the initial blocks)
      if ((^clk_cnt_i) === 1'bx) begin
        cs = "0";
      end
      else begin
        $sformat(cs, "%0d", clk_cnt_i);
      end
      $sformat(r, "[t=%0s ns clk=%0s]", pad_left(ts, TIME_W), pad_left(cs, CLK_W));
      prefix = r;
    end
  endfunction

  // ------------------------------------------------------------------
  // Value formats by meaning (radix only changes the text, never the
  // width or the comparison). v holds up to 64 bits, w = width in bits.
  // ------------------------------------------------------------------
  function [63:0] wmask;
    input integer w;
    begin
      if (w >= 64) begin
        wmask = {64{1'b1}};
      end
      else begin
        wmask = (64'h1 << w) - 64'h1;
      end
    end
  endfunction

  // Hex with 0x, upper-case digits and the full width: addresses, raw
  // data, configuration, masks (x / z stay lower-case)
  function [8*80-1:0] fmt_hex;
    input [63:0]  v;
    input integer w;
    reg   [8*80-1:0] t;
    reg   [8*80-1:0] r;
    reg   [7:0]      ch;
    integer          nd;
    integer          k;
    begin
      nd = (w + 3) / 4;
      $sformat(t, "%h", v & wmask(w));
      r = 0;
      for (k = 0; k < nd; k = k + 1) begin
        ch = t[8*k +: 8];
        if (ch >= "a" && ch <= "f") begin
          ch = ch - 8'h20;
        end
        r[8*k +: 8] = ch;
      end
      r[8*nd +: 8]     = "x";
      r[8*(nd+1) +: 8] = "0";
      fmt_hex = r;
    end
  endfunction

  // Binary with 0b and the full width: byte strobes, control bit groups
  function [8*80-1:0] fmt_bin;
    input [63:0]  v;
    input integer w;
    reg   [8*80-1:0] t;
    reg   [8*80-1:0] r;
    integer          k;
    begin
      $sformat(t, "%b", v & wmask(w));
      r = 0;
      for (k = 0; k < w; k = k + 1) begin
        r[8*k +: 8] = t[8*k +: 8];
      end
      r[8*w +: 8]     = "b";
      r[8*(w+1) +: 8] = "0";
      fmt_bin = r;
    end
  endfunction

  // Unsigned decimal, full width (64-bit counters included); X/Z is shown
  // as raw hex, never as a plausible number
  function [8*80-1:0] fmt_dec;
    input [63:0]  v;
    input integer w;
    reg   [63:0]     vm;
    reg   [8*80-1:0] r;
    begin
      vm = v & wmask(w);
      if ((^vm) === 1'bx) begin
        $sformat(r, "X/Z %0s", fmt_hex(v, w));
      end
      else begin
        $sformat(r, "%0d", vm);
      end
      fmt_dec = r;
    end
  endfunction

  // Counter value: decimal with its unit (X/Z keeps the raw hex)
  function [8*80-1:0] fmt_cnt;
    input [63:0]  v;
    input integer w;
    reg   [8*80-1:0] r;
    begin
      if ((^(v & wmask(w))) === 1'bx) begin
        r = fmt_dec(v, w);
      end
      else begin
        $sformat(r, "%0s counts", fmt_dec(v, w));
      end
      fmt_cnt = r;
    end
  endfunction

  // Signed (two's complement) decimal of a w-bit value
  function [8*80-1:0] fmt_sdec;
    input [63:0]  v;
    input integer w;
    reg   [63:0]     vm;
    reg   [8*80-1:0] r;
    begin
      vm = v & wmask(w);
      if ((^vm) === 1'bx) begin
        $sformat(r, "X/Z %0s", fmt_hex(v, w));
      end
      else if (vm[w-1]) begin
        $sformat(r, "-%0d", (~vm + 64'h1) & wmask(w));
      end
      else begin
        $sformat(r, "%0d", vm);
      end
      fmt_sdec = r;
    end
  endfunction

  // One control bit: 0 / 1 / x / z
  function [8*80-1:0] fmt_bit;
    input v;
    reg   [8*80-1:0] r;
    begin
      $sformat(r, "%b", v);
      fmt_bit = r;
    end
  endfunction

  // ------------------------------------------------------------------
  // Column alignment (Verilog-2005, no %-40s / %8d field widths)
  // ------------------------------------------------------------------
  function integer str_len;
    input [8*80-1:0] s;
    integer          k;
    begin
      str_len = 0;
      for (k = 0; k < 80; k = k + 1) begin
        if (s[8*k +: 8] != 8'h0) begin
          str_len = k + 1;
        end
      end
    end
  endfunction

  // s right-aligned in a field of w characters
  function [8*80-1:0] pad_left;
    input [8*80-1:0] s;
    input integer    w;
    integer          k;
    begin
      pad_left = s;
      for (k = str_len(s); k < w; k = k + 1) begin
        pad_left[8*k +: 8] = " ";
      end
    end
  endfunction

  // s left-aligned in a field of w characters
  function [8*80-1:0] pad_right;
    input [8*80-1:0] s;
    input integer    w;
    integer          k;
    begin
      pad_right = s;
      for (k = str_len(s); k < w; k = k + 1) begin
        pad_right = {pad_right[8*79-1:0], 8'h20};
      end
    end
  endfunction

endmodule
