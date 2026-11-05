// ============================================================================
// Component : tb_timer_top_chk - checker of tb_timer_top
// Inputs    : expected outputs exp_* from u_model, sampled pins, sample time
//             and transfer status (s_done, s_wait, s_setup) from u_mon.
//             Every expected value comes from the model; the test case never
//             passes one.
// Results   : tb_timer_top.u_log.check (counted) / info (not counted), with
//             the time of the sample (falling edge), not the compare time.
//             A deviation is one line: its short context is the note in
//             parentheses after FAIL (no separate diagnosis line).
// Timing    : handles each valid monitor sample at falling edge + CHK_DLY
//             (sample and model outputs stable; stimulus only changes at
//             posedge + #1):
//   - transfer completion (s_done), one line per transfer:
//       APB WRITE <REG> addr data strb OK|SLVERR   response as the model
//         predicts (tim_pslverr, one wait state): event line, not a check -
//         OK only says the transfer completed without an error response
//       APB WRITE <REG> ... expected: <e> actual: <a> FAIL (<note>)
//         response differs; note = wait cycles and setup clk, or the TCR
//         error condition of the model
//       APB READ <REG> addr expected: <e> actual: <a> PASS|FAIL [(<note>)]
//         read data (decimal counts for TDR0/TDR1, hex otherwise) and
//         response; note = fields that differ (registers) or the response
//         deviation; none for a count or an X/Z value
//   - watch of every other sample: tim_pready, tim_pslverr, tim_prdata
//       against the model, tim_int on every sample. Nothing is printed
//       while they match. The first mismatch of an output prints one
//       "[WATCH] <signal> (<bus situation>) expected: <e> actual: <a> FAIL"
//       (one count); repeats of that output are only counted and closed
//       by a [WATCH END] line (not counted) when it matches again; another
//       output, or the same output after it matched again, prints its own
//       FAIL
//   - checkpoint(what): one "[CHECK] tim_int <what> ..." of the sample
//       just processed (a moment the test case names), expected from the
//       model
//   - sync: the caller returns after this sample is processed
// Ownership : compare process: bad, bad_n, bad_c, m_wait, m_done, last_*,
//             sync_ack and the line variables; test sequence: sync_req
// ============================================================================
`timescale 1ns/1ps

module tb_timer_top_chk #(
  parameter CHK_DLY = 1
) (
  input  wire        clk_i,
  input  wire [31:0] clk_cnt_i,
  input  wire [63:0] s_time_i,
  input  wire        s_rst_n_i,
  input  wire        s_psel_i,
  input  wire        s_penable_i,
  input  wire        s_pwrite_i,
  input  wire [11:0] s_paddr_i,
  input  wire [31:0] s_pwdata_i,
  input  wire [3:0]  s_pstrb_i,
  input  wire [31:0] s_prdata_i,
  input  wire        s_pready_i,
  input  wire        s_pslverr_i,
  input  wire        s_tim_int_i,
  input  wire        s_done_i,
  input  wire [7:0]  s_wait_i,
  input  wire [31:0] s_setup_i,
  input  wire        s_vld_i,
  input  wire [31:0] exp_prdata_i,
  input  wire        exp_pready_i,
  input  wire        exp_pslverr_i,
  input  wire        exp_tim_int_i
);

  localparam [9:0] W_TDR0 = 10'h001;
  localparam [9:0] W_TDR1 = 10'h002;

  integer          sync_req;
  integer          sync_ack;
  reg  [3:0]       bad;
  integer          bad_n [0:3];
  integer          bad_c [0:3];
  integer          m_wait;
  reg              m_done;
  reg  [63:0]      last_t;
  reg              last_e_int;
  reg              last_a_int;
  reg              acc;
  reg              rsp_ok;
  reg              dat_ok;
  reg              is_cnt;
  reg  [8*64-1:0]  tag;
  reg  [8*200-1:0] txt;
  reg  [8*80-1:0]  es;
  reg  [8*80-1:0]  as;
  reg  [8*120-1:0] nt;
  reg  [8*200-1:0] m;
  reg  [8*120-1:0] bd;

  initial begin
    sync_req = 0;
    sync_ack = 0;
    bad      = 4'h0;
    m_wait   = 0;
    m_done   = 1'b0;
  end

  // ------------------------------------------------------------------
  // Calls of the test sequence (through tb_timer_top)
  // ------------------------------------------------------------------

  // Returns after the sample of the current (or next) falling edge has
  // been checked, so a following branch header owns only later checks
  task sync;
    begin
      sync_req = sync_req + 1;
      wait (sync_ack == sync_req);
    end
  endtask

  // tim_int of the sample just processed against the model (call right
  // after a sequence task). The test case names the moment only.
  task checkpoint;
    input [8*64-1:0] what;
    begin
      $sformat(txt, "tim_int %0s", what);
      tb_timer_top.u_log.check(last_t, "CHECK", txt, (last_a_int === last_e_int),
                               tb_timer_top.u_log.fmt_bit(last_e_int),
                               tb_timer_top.u_log.fmt_bit(last_a_int), 0, "");
    end
  endtask

  // ------------------------------------------------------------------
  // Bus situation of the current sample (context of a watch FAIL)
  // ------------------------------------------------------------------
  task bus_desc;
    begin
      if (s_rst_n_i !== 1'b1) begin
        bd = "in reset";
      end
      else if (s_psel_i !== 1'b1) begin
        bd = "bus idle";
      end
      else if (s_penable_i !== 1'b1) begin
        $sformat(bd, "setup of APB %0s %0s", s_pwrite_i ? "WRITE" : "READ",
                 tb_timer_top.reg_name(s_paddr_i));
      end
      else begin
        $sformat(bd, "access cycle %0d of APB %0s %0s, setup clk=%0d", s_wait_i,
                 s_pwrite_i ? "WRITE" : "READ", tb_timer_top.reg_name(s_paddr_i), s_setup_i);
      end
    end
  endtask

  // ------------------------------------------------------------------
  // Watch of one output on a sample that is not a transfer completion:
  // silent while it matches; the first mismatch prints one FAIL line
  // "[WATCH] <output> (<bus situation>) expected: <e> actual: <a> FAIL";
  // repeats are counted and closed by one [WATCH END] line (not counted)
  // ------------------------------------------------------------------
  task watch;
    input integer    k;
    input [8*16-1:0] name;
    input [31:0]     e;
    input [31:0]     a;
    input integer    wb;
    begin
      if (a !== e) begin
        if (!bad[k]) begin
          bad[k]   = 1'b1;
          bad_n[k] = 1;
          bad_c[k] = clk_cnt_i;
          es = (wb == 1) ? tb_timer_top.u_log.fmt_bit(e[0]) : tb_timer_top.u_log.fmt_hex(e, wb);
          as = (wb == 1) ? tb_timer_top.u_log.fmt_bit(a[0]) : tb_timer_top.u_log.fmt_hex(a, wb);
          bus_desc;
          $sformat(txt, "%0s (%0s)", name, bd);
          tb_timer_top.u_log.check(s_time_i, "WATCH", txt, 1'b0, es, as, 0, "");
        end
        else begin
          bad_n[k] = bad_n[k] + 1;
        end
      end
      else if (bad[k]) begin
        bad[k] = 1'b0;
        $sformat(m, "%0s: %0d mismatching sample(s) clk=%0d..%0d, matches the model again",
                 name, bad_n[k], bad_c[k], clk_cnt_i - 1);
        tb_timer_top.u_log.info(s_time_i, "WATCH END", m);
      end
    end
  endtask

  // ------------------------------------------------------------------
  // One transfer completion (DUT pready = 1 in an access cycle): one line
  // ------------------------------------------------------------------
  task check_txn;
    begin
      rsp_ok = (exp_pready_i === 1'b1) && (s_pslverr_i === exp_pslverr_i) && (s_wait_i == m_wait);
      // Short context of a response deviation
      if (s_wait_i != m_wait || exp_pready_i !== 1'b1) begin
        $sformat(nt, "%0d wait, model %0d, setup clk=%0d", s_wait_i, m_wait, s_setup_i);
      end
      else if (s_pslverr_i !== exp_pslverr_i) begin
        $sformat(nt, "tim_pslverr %b, %0s", s_pslverr_i, tb_timer_top.u_model.err_text(1'b0));
      end
      else begin
        nt = "";
      end
      if (s_pwrite_i) begin
        $sformat(tag, "APB WRITE %0s", tb_timer_top.reg_name(s_paddr_i));
        $sformat(txt, "addr: %0s data: %0s strb: %0s", tb_timer_top.u_log.fmt_hex(s_paddr_i, 12),
                 tb_timer_top.u_log.fmt_hex(s_pwdata_i, 32), tb_timer_top.u_log.fmt_bin(s_pstrb_i, 4));
        if (rsp_ok) begin
          $sformat(m, "%0s %0s", txt, (s_pslverr_i === 1'b1) ? "SLVERR" : "OK");
          tb_timer_top.u_log.info(s_time_i, tag, m);
        end
        else if (s_pslverr_i !== exp_pslverr_i) begin
          tb_timer_top.u_log.check(s_time_i, tag, txt, 1'b0, exp_pslverr_i ? "SLVERR" : "OK",
                                   (s_pslverr_i === 1'b1) ? "SLVERR" :
                                   (s_pslverr_i === 1'b0) ? "OK" : "X/Z", 0, nt);
        end
        else begin
          $sformat(es, "%0d wait", m_wait);
          $sformat(as, "%0d wait", s_wait_i);
          tb_timer_top.u_log.check(s_time_i, tag, txt, 1'b0, es, as, 0, nt);
        end
      end
      else begin
        $sformat(tag, "APB READ %0s", tb_timer_top.reg_name(s_paddr_i));
        $sformat(txt, "addr: %0s", tb_timer_top.u_log.fmt_hex(s_paddr_i, 12));
        is_cnt = (s_paddr_i[11:2] == W_TDR0) || (s_paddr_i[11:2] == W_TDR1);
        if (is_cnt) begin
          es = tb_timer_top.u_log.fmt_cnt(exp_prdata_i, 32);
          as = tb_timer_top.u_log.fmt_cnt(s_prdata_i, 32);
        end
        else begin
          es = tb_timer_top.u_log.fmt_hex(exp_prdata_i, 32);
          as = tb_timer_top.u_log.fmt_hex(s_prdata_i, 32);
        end
        dat_ok = (s_prdata_i === exp_prdata_i);
        // A register (hex) mismatch names the fields; a count or an X/Z
        // value needs nothing more than expected / actual
        if (!dat_ok && !is_cnt && (^s_prdata_i) !== 1'bx && nt == 0) begin
          $sformat(nt, "differ: %0s", tb_timer_top.field_names(s_paddr_i, s_prdata_i ^ exp_prdata_i));
        end
        tb_timer_top.u_log.check(s_time_i, tag, txt, dat_ok && rsp_ok, es, as, tb_timer_top.VAL_W, nt);
      end
    end
  endtask

  // ------------------------------------------------------------------
  // Compare process
  // ------------------------------------------------------------------
  always @(negedge clk_i) begin
    #(CHK_DLY);
    if (s_vld_i) begin
      acc = (s_psel_i === 1'b1) && (s_penable_i === 1'b1);
      // Wait cycles the model predicts for the transfer on the bus
      if (acc && !m_done) begin
        if (exp_pready_i === 1'b1) begin
          m_done = 1'b1;
        end
        else begin
          m_wait = m_wait + 1;
        end
      end
      if (s_done_i) begin
        check_txn;
        m_wait = 0;
        m_done = 1'b0;
      end
      else begin
        watch(0, "tim_pready",  {31'h0, exp_pready_i},  {31'h0, s_pready_i},  1);
        watch(1, "tim_pslverr", {31'h0, exp_pslverr_i}, {31'h0, s_pslverr_i}, 1);
        watch(2, "tim_prdata",  exp_prdata_i,           s_prdata_i,           32);
        if (!acc) begin
          m_wait = 0;
          m_done = 1'b0;
        end
      end
      watch(3, "tim_int", {31'h0, exp_tim_int_i}, {31'h0, s_tim_int_i}, 1);
      last_t     = s_time_i;
      last_e_int = exp_tim_int_i;
      last_a_int = s_tim_int_i;
    end
    sync_ack = sync_req;
  end

endmodule
