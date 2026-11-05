// ============================================================================
// TC_TIMER_TOP_012 - cnt_halt_chk
// Objective: cnt_ctrl debug halt seen through timer_top: halted =
//            dbg_mode & THCSR.HALT_REQ holds TDR0 (and the divider
//            position); HALT_ACK reads the halt; ending either condition
//            resumes counting; no TDR write while halted (TIM_EN = 1)
//   Halt in debug mode      : dbg_mode = 1, then HALT_REQ = 1 halts,
//                             HALT_REQ = 0 resumes
//   Halt without debug mode : HALT_REQ = 1, then dbg_mode = 1 halts,
//                             dbg_mode = 0 resumes with HALT_REQ = 1 kept
//   TDR write while halted
// Stimulus : example scenario of the S5 skill (operations and checkpoints of
//            a halt/resume); the first two branches differ from the Test
//            sequence of doc/vplan/timer_top_vplan.md and change dbg_mode
//            while TIM_EN = 1, outside the OPEN-001 environment assumption
//            (dbg_mode is synchronous, driven at posedge + #1). No expected
//            value here - u_chk checks every transfer and every sample
//            against u_model.
// Copied to sim/run_test.v and included inside tb_timer_top.
// ============================================================================
  initial begin
    init_test("TC_TIMER_TOP_012",
              "cnt_ctrl debug halt through timer_top: dbg_mode & HALT_REQ holds the counter, HALT_ACK, resume by HALT_REQ or by dbg_mode");
    u_log.item("cnt_halt_chk");
    begin : halt_in_debug_mode
      u_log.sub1("Halt in debug mode");
      u_log.goal("DIV_VAL 1 (1 step / 2 cycles): dbg_mode = 1 alone does not halt; HALT_REQ = 1 halts (TDR0 and divider phase held); HALT_REQ = 0 resumes");
      reset_dut;
      apb_write(ADDR_TCR,   32'h0000_0103, 4'b0011);     // DIV_VAL = 1, DIV_EN = 1, TIM_EN = 1
      apb_read(ADDR_TDR0);                               // counting
      set_dbg_mode(1'b1);                                // HALT_REQ = 0: no halt yet
      apb_write(ADDR_THCSR, 32'h0000_0001, 4'b0001);     // HALT_REQ = 1: halt starts
      apb_read(ADDR_THCSR);                              // HALT_REQ, HALT_ACK
      apb_read(ADDR_TDR0);                               // held
      wait_cycles(8);
      apb_read(ADDR_TDR0);                               // still held
      apb_write(ADDR_THCSR, 32'h0000_0000, 4'b0001);     // HALT_REQ = 0: resume
      apb_read(ADDR_THCSR);
      apb_read(ADDR_TDR0);                               // counting again, same divider phase
    end
    begin : halt_without_debug_mode
      u_log.sub1("Halt without debug mode");
      u_log.goal("DIV_EN 0 (1 step / cycle): HALT_REQ = 1 then dbg_mode = 1 halts; dbg_mode = 0 with HALT_REQ = 1 kept: HALT_ACK 0, counting resumes");
      reset_dut;
      apb_write(ADDR_TCR,   32'h0000_0001, 4'b0001);     // TIM_EN = 1, DIV_EN = 0
      apb_read(ADDR_TDR0);                               // counting
      apb_write(ADDR_THCSR, 32'h0000_0001, 4'b0001);     // HALT_REQ = 1, dbg_mode 0: no halt
      set_dbg_mode(1'b1);                                // halt starts
      apb_read(ADDR_THCSR);                              // HALT_REQ, HALT_ACK
      apb_read(ADDR_TDR0);                               // held
      wait_cycles(8);
      apb_read(ADDR_TDR0);                               // still held
      set_dbg_mode(1'b0);                                // HALT_REQ alone: resume
      apb_read(ADDR_THCSR);
      apb_read(ADDR_TDR0);                               // counting again
    end
    begin : tdr_write_while_halted
      u_log.sub1("TDR write while halted");
      u_log.goal("halted with TIM_EN = 1: a TDR0 write completes without error but is ignored");
      reset_dut;
      set_dbg_mode(1'b1);                                // before the timer starts
      apb_write(ADDR_TCR,   32'h0000_0001, 4'b0001);     // TIM_EN = 1, DIV_EN = 0
      apb_write(ADDR_THCSR, 32'h0000_0001, 4'b0001);     // HALT_REQ = 1: halt
      apb_write(ADDR_TDR0,  32'h0000_0077, 4'b1111);     // ignored: TIM_EN = 1
      apb_read(ADDR_TDR0);
      apb_read(ADDR_THCSR);
    end
    end_test;
  end
