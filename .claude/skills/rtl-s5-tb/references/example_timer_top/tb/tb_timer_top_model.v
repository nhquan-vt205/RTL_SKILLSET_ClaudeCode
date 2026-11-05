// ============================================================================
// Component : tb_timer_top_model - golden reference model of timer_top
// Inputs    : clk, asynchronous reset, DUT inputs as sampled by u_mon. Never
//             a DUT output, never a DUT internal signal: the APB wait state
//             is fixed by the spec, so the model predicts tim_pready itself
//             and u_chk checks the DUT handshake against it.
// Drives    : exp_prdata_o, exp_pready_o, exp_pslverr_o, exp_tim_int_o -> u_chk
// Behavior  : written from the spec text, not from the RTL structure:
//   apb_slave_spec   - transfer = setup, wait (1st access cycle, pready 0),
//                      last access cycle (pready 1); only a setup phase
//                      starts a transfer (an access held after the
//                      predicted completion is not a new one, so a late
//                      DUT pready gives one FAIL, not a stream of them);
//                      a write takes effect at the edge ending the last
//                      access cycle; the TCR error is decided in the wait
//                      cycle; read data only in the last access cycle of a
//                      read, else 0
//   register_map     - TCR / TCMP0 / TCMP1 / TIER / THCSR with byte strobes,
//                      TISR.INT_ST RW1C, reserved RAZ/WI, TCR error
//                      conditions 1-3, TDR0/TDR1 writable only while
//                      TIM_EN = 0 (OPEN-002), reset values
//   cnt_ctrl_spec    - count every cycle (DIV_EN 0) or one step every
//                      2^DIV_VAL running cycles from a fresh divider period
//                      (DIV_EN 1); dbg_mode & HALT_REQ holds counter and
//                      divider position; TIM_EN 1 -> 0 clears the counter
//                      one cycle later
//   timer_top_spec   - INT_ST set one cycle after cnt == {TCMP1, TCMP0},
//                      write-1 clear wins; tim_int = INT_ST & INT_EN
//             State moves at the rising edge with the inputs sampled in the
//             cycle that ends there, so every cycle of an APB transfer
//             (setup, wait, last access) and every idle cycle counts;
//             expected outputs are combinational from the state and the
//             current sample.
// Log       : none. err_text() names the TCR error condition behind
//             exp_pslverr_o for the note of a FAIL line of u_chk.
// Ownership : state (posedge process), combinational values (always @*)
// ============================================================================
`timescale 1ns/1ps

module tb_timer_top_model (
  input  wire        clk_i,
  input  wire        rst_n_i,
  input  wire        s_psel_i,
  input  wire        s_penable_i,
  input  wire        s_pwrite_i,
  input  wire [11:0] s_paddr_i,
  input  wire [31:0] s_pwdata_i,
  input  wire [3:0]  s_pstrb_i,
  input  wire        s_dbg_mode_i,
  output reg  [31:0] exp_prdata_o,
  output reg         exp_pready_o,
  output reg         exp_pslverr_o,
  output reg         exp_tim_int_o
);

  // Word offsets (paddr[11:2]) of the register map
  localparam [9:0] W_TCR   = 10'h000;
  localparam [9:0] W_TDR0  = 10'h001;
  localparam [9:0] W_TDR1  = 10'h002;
  localparam [9:0] W_TCMP0 = 10'h003;
  localparam [9:0] W_TCMP1 = 10'h004;
  localparam [9:0] W_TIER  = 10'h005;
  localparam [9:0] W_TISR  = 10'h006;
  localparam [9:0] W_THCSR = 10'h007;

  // Specified state
  reg         in_xfer;     // a setup phase started the transfer on the bus
  reg         acc_seen;    // wait cycle of the current transfer is over
  reg         err_q;       // TCR error decided in the wait cycle
  reg         tim_en;
  reg         div_en;
  reg  [3:0]  div_val;
  reg  [31:0] tcmp0;
  reg  [31:0] tcmp1;
  reg         int_en;
  reg         int_st;
  reg         halt_req;
  reg  [63:0] cnt;         // {TDR1, TDR0}
  reg  [8:0]  pos;         // divider position: running cycles mod 2^DIV_VAL
  reg         en_prev;     // TIM_EN of the previous cycle

  // Combinational values of the current cycle
  reg  [9:0]  w;
  reg         acc;
  reg         done;
  reg         wr_acc;
  reg         rd_acc;
  reg         err1;
  reg         err2;
  reg         err3;
  reg         tcr_err;
  reg         halted;
  reg  [8:0]  ivl;
  reg         step;
  reg         clr_now;
  reg         tdr_wr;
  reg         int_clr;
  reg         match;
  reg         ton;
  reg  [63:0] cnt_nx;
  reg  [8:0]  pos_nx;
  reg  [31:0] rd_val;
  reg  [31:0] tcr_val;
  reg  [31:0] tcr_nx;

  // Software write of TDR0 (hi = 0) or TDR1 (hi = 1), strobed bytes only
  function [63:0] tdr_merge;
    input [63:0] old;
    input        hi;
    input [3:0]  strb;
    input [31:0] wdata;
    integer      k;
    begin
      tdr_merge = old;
      for (k = 0; k < 4; k = k + 1) begin
        if (strb[k]) begin
          tdr_merge[32 * hi + 8 * k +: 8] = wdata[8 * k +: 8];
        end
      end
    end
  endfunction

  // Strobed byte write of a 32-bit register
  function [31:0] byte_merge;
    input [31:0] old;
    input [3:0]  strb;
    input [31:0] wdata;
    integer      k;
    begin
      byte_merge = old;
      for (k = 0; k < 4; k = k + 1) begin
        if (strb[k]) begin
          byte_merge[8 * k +: 8] = wdata[8 * k +: 8];
        end
      end
    end
  endfunction

  // ------------------------------------------------------------------
  // Expected outputs and next state of the current cycle
  // ------------------------------------------------------------------
  always @(*) begin
    w       = s_paddr_i[11:2];
    // An access cycle needs psel = penable = 1 after a setup phase of the
    // same transfer (an X bus is no transfer; an access held after the
    // predicted completion is not a new transfer)
    acc     = (s_psel_i === 1'b1) && (s_penable_i === 1'b1) && in_xfer;
    done    = acc && acc_seen;
    // TCR error conditions 1-3 (register map, stored TIM_EN/DIV_EN/DIV_VAL)
    err1    = s_pstrb_i[1] && (s_pwdata_i[11:8] > 4'd8);
    err2    = tim_en && s_pstrb_i[1] && (s_pwdata_i[11:8] != div_val);
    err3    = tim_en && s_pstrb_i[0] && (s_pwdata_i[1] != div_en);
    tcr_err = (w == W_TCR) && (err1 || err2 || err3);
    wr_acc  = done && (s_pwrite_i === 1'b1) && !err_q;
    rd_acc  = done && (s_pwrite_i === 1'b0);
    halted  = (s_dbg_mode_i === 1'b1) && halt_req;
    ivl     = 9'd1 << div_val;
    step    = tim_en && !halted && (!div_en || (pos == ivl - 9'd1));
    clr_now = en_prev && !tim_en;
    tdr_wr  = wr_acc && !tim_en && ((w == W_TDR0) || (w == W_TDR1));
    int_clr = wr_acc && (w == W_TISR) && s_pstrb_i[0] && s_pwdata_i[0];
    ton     = wr_acc && (w == W_TCR) && s_pstrb_i[0] && s_pwdata_i[0] && !tim_en;
    match   = (cnt == {tcmp1, tcmp0});

    // Counter: clear > software write > count step
    if (clr_now) begin
      cnt_nx = 64'h0;
    end
    else if (tdr_wr) begin
      cnt_nx = tdr_merge(cnt, (w == W_TDR1), s_pstrb_i, s_pwdata_i);
    end
    else begin
      cnt_nx = step ? cnt + 64'd1 : cnt;
    end

    // Divider position: fresh period while TIM_EN = 0 or DIV_EN = 0,
    // held while halted
    if (!tim_en || !div_en) begin
      pos_nx = 9'd0;
    end
    else begin
      pos_nx = halted ? pos : ((pos == ivl - 9'd1) ? 9'd0 : pos + 9'd1);
    end

    tcr_val = {20'h0, div_val, 6'h0, div_en, tim_en};
    tcr_nx  = {20'h0, s_pstrb_i[1] ? s_pwdata_i[11:8] : div_val, 6'h0,
               s_pstrb_i[0] ? s_pwdata_i[1] : div_en,
               s_pstrb_i[0] ? s_pwdata_i[0] : tim_en};
    case (w)
      W_TCR   : rd_val = tcr_val;
      W_TDR0  : rd_val = cnt[31:0];
      W_TDR1  : rd_val = cnt[63:32];
      W_TCMP0 : rd_val = tcmp0;
      W_TCMP1 : rd_val = tcmp1;
      W_TIER  : rd_val = {31'h0, int_en};
      W_TISR  : rd_val = {31'h0, int_st};
      W_THCSR : rd_val = {30'h0, halted, halt_req};
      default : rd_val = 32'h0;
    endcase

    exp_pready_o  = done;
    exp_pslverr_o = done && err_q;
    exp_prdata_o  = rd_acc ? rd_val : 32'h0;
    exp_tim_int_o = int_st && int_en;
  end

  // ------------------------------------------------------------------
  // State update at the rising edge; asynchronous reset to the
  // register-map reset values
  // ------------------------------------------------------------------
  always @(posedge clk_i or negedge rst_n_i) begin
    if (!rst_n_i) begin
      in_xfer  <= 1'b0;
      acc_seen <= 1'b0;
      err_q    <= 1'b0;
      tim_en   <= 1'b0;
      div_en   <= 1'b0;
      div_val  <= 4'h1;
      tcmp0    <= 32'hFFFF_FFFF;
      tcmp1    <= 32'hFFFF_FFFF;
      int_en   <= 1'b0;
      int_st   <= 1'b0;
      halt_req <= 1'b0;
      cnt      <= 64'h0;
      pos      <= 9'd0;
      en_prev  <= 1'b0;
    end
    else begin
      // APB: setup starts a transfer; the cycle after the first access
      // cycle completes it
      if ((s_psel_i === 1'b1) && (s_penable_i === 1'b0)) begin
        in_xfer <= 1'b1;
      end
      else if (done || (s_psel_i !== 1'b1)) begin
        in_xfer <= 1'b0;
      end
      acc_seen <= acc && !acc_seen;
      err_q    <= acc && !acc_seen && (s_pwrite_i === 1'b1) && tcr_err;

      cnt     <= cnt_nx;
      pos     <= pos_nx;
      en_prev <= tim_en;

      // Interrupt status: write-1 clear > set > hold
      if (int_clr) begin
        int_st <= 1'b0;
      end
      else if (match) begin
        int_st <= 1'b1;
      end

      // Accepted register writes (byte strobes)
      if (wr_acc) begin
        case (w)
          W_TCR: begin
            if (s_pstrb_i[0]) begin
              tim_en <= s_pwdata_i[0];
              div_en <= s_pwdata_i[1];
            end
            if (s_pstrb_i[1]) begin
              div_val <= s_pwdata_i[11:8];
            end
          end
          W_TCMP0: begin
            tcmp0 <= byte_merge(tcmp0, s_pstrb_i, s_pwdata_i);
          end
          W_TCMP1: begin
            tcmp1 <= byte_merge(tcmp1, s_pstrb_i, s_pwdata_i);
          end
          W_TIER: begin
            if (s_pstrb_i[0]) begin
              int_en <= s_pwdata_i[0];
            end
          end
          W_THCSR: begin
            if (s_pstrb_i[0]) begin
              halt_req <= s_pwdata_i[0];
            end
          end
          default: begin
          end
        endcase
      end
    end
  end

  // TCR error condition behind exp_pslverr_o of the current completion
  // (FAIL note of u_chk; err1..err3 still hold the conditions of the
  // transfer: inputs and state are unchanged until the edge that ends it)
  function [8*80-1:0] err_text;
    input dummy;
    begin
      if (!err_q) begin
        err_text = "model: no TCR error condition";
      end
      else if (err1) begin
        err_text = "model: TCR error condition 1, DIV_VAL > 8";
      end
      else if (err2) begin
        err_text = "model: TCR error condition 2, DIV_VAL change while TIM_EN = 1";
      end
      else begin
        err_text = "model: TCR error condition 3, DIV_EN change while TIM_EN = 1";
      end
    end
  endfunction

endmodule
