// ============================================================================
// TC_TIMER_TOP_006 - cnt_ctrl_chk
// Objective: cnt_ctrl count enable seen through timer_top: TIM_EN start/stop
//            with hardware clear, count speed by DIV_EN / DIV_VAL, no TDR
//            write while the timer runs
//   Timer enable, Divider setting, TDR write while counting
// Stimulus : the Test sequence of the VPLAN; no expected value here - u_chk
//            checks every transfer and every sample against u_model.
// Copied to sim/run_test.v and included inside tb_timer_top.
// ============================================================================
  initial begin
    init_test("TC_TIMER_TOP_006",
              "cnt_ctrl count enable through timer_top: TIM_EN start/stop and hardware clear, count interval 2^DIV_VAL, TDR writes ignored while TIM_EN = 1");
    u_log.item("cnt_ctrl_chk");
    begin : timer_enable
      u_log.sub1("Timer enable");
      u_log.goal("TIM_EN 0 -> 1 counts every cycle (DIV_EN 0); TIM_EN 1 -> 0 clears TDR0/TDR1; a TDR0 load while stopped is kept and counting resumes from it");
      reset_dut;
      apb_write(ADDR_TCR,  32'h0000_0001, 4'b0001);      // TIM_EN = 1
      apb_read(ADDR_TDR0);
      apb_write(ADDR_TCR,  32'h0000_0000, 4'b0001);      // TIM_EN = 0
      apb_read(ADDR_TDR0);
      apb_read(ADDR_TDR1);
      apb_write(ADDR_TDR0, 32'h0000_0055, 4'b1111);      // load while stopped
      wait_cycles(5);
      apb_read(ADDR_TDR0);
      apb_write(ADDR_TCR,  32'h0000_0001, 4'b0001);      // TIM_EN = 1
      apb_read(ADDR_TDR0);
    end
    begin : divider_setting
      u_log.sub1("Divider setting");
      u_log.goal("DIV_EN 1: one step every 2^DIV_VAL cycles from a fresh divider period, DIV_VAL 0 / 2 / 8; the cycles of the APB reads count too");
      reset_dut;
      // Part A: DIV_VAL = 0
      apb_write(ADDR_TCR, 32'h0000_0002, 4'b0011);
      apb_write(ADDR_TCR, 32'h0000_0003, 4'b0011);
      apb_read(ADDR_TDR0);
      apb_read(ADDR_TDR0);
      apb_read(ADDR_TDR0);
      // Part B: DIV_VAL = 2
      apb_write(ADDR_TCR, 32'h0000_0002, 4'b0001);       // TIM_EN = 0, clears
      apb_write(ADDR_TCR, 32'h0000_0202, 4'b0011);
      apb_write(ADDR_TCR, 32'h0000_0203, 4'b0011);
      apb_read(ADDR_TDR0);
      apb_read(ADDR_TDR0);
      apb_read(ADDR_TDR0);
      apb_read(ADDR_TDR0);
      apb_read(ADDR_TDR0);
      // Part C: DIV_VAL = 8
      apb_write(ADDR_TCR, 32'h0000_0202, 4'b0001);
      apb_write(ADDR_TCR, 32'h0000_0802, 4'b0011);
      apb_write(ADDR_TCR, 32'h0000_0803, 4'b0011);
      wait_cycles(253);
      apb_read(ADDR_TDR0);
      apb_read(ADDR_TDR0);
    end
    begin : tdr_write_while_counting
      u_log.sub1("TDR write while counting");
      u_log.goal("TIM_EN 1: TDR0/TDR1 writes complete without error and change neither counter nor divider (DIV_VAL 2); after TIM_EN 0 a TDR0 write is accepted");
      reset_dut;
      apb_write(ADDR_TCR,  32'h0000_0202, 4'b0011);      // DIV_VAL = 2
      apb_write(ADDR_TCR,  32'h0000_0203, 4'b0011);      // TIM_EN = 1
      apb_write(ADDR_TDR0, 32'h0000_0100, 4'b1111);      // ignored
      apb_read(ADDR_TDR0);
      apb_read(ADDR_TDR0);
      apb_write(ADDR_TDR0, 32'h0000_0200, 4'b1111);      // ignored
      apb_read(ADDR_TDR0);
      apb_read(ADDR_TDR0);
      apb_write(ADDR_TDR1, 32'h0000_0001, 4'b1111);      // ignored
      apb_read(ADDR_TDR1);
      apb_read(ADDR_TDR0);
      apb_write(ADDR_TCR,  32'h0000_0202, 4'b0001);      // TIM_EN = 0
      apb_write(ADDR_TDR0, 32'h0000_0055, 4'b1111);      // accepted
      apb_read(ADDR_TDR0);
    end
    end_test;
  end
