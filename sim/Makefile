##############################################################################################
# Simulation environment (shared by every module)
#   Simulation / waveform / coverage : QuestaSim 2021 (vlog, vsim, vcover)
#   Schematic                         : Vivado (RTL elaboration of rtl.f)
# Test case TC_<MODULE>_<NNN> = testcases/TC_<MODULE>_<NNN>.v, run on tb/tb_<module>.v
# Example run string: make TESTNAME={name_of_testcase} {optional}
#                     make TESTNAME=TC_MY_MODULE_002 all
#                     make DATA_IN=<input.txt> DATA_OUT=<output.txt> all   (paths relative to sim/)
#                     make gen_data                                       (script/<module>_gen_vectors.py)
#                     make schematic SCH=u_ctrl                           (MODULE=<m> for another top)
##############################################################################################
#Define variables
REGRESS_LIST ?= pat.list
TESTNAME     ?= $(firstword $(shell sed '/\/\//d' $(REGRESS_LIST)))
# Module under test from the test name: TC_MY_MODULE_002 -> my_module
MODULE       ?= $(shell echo $(TESTNAME) | sed 's/^TC_//; s/_[0-9]*$$//' | tr A-Z a-z)
TB_NAME      ?= tb_$(MODULE)
RADIX        ?= decimal
# tb.f reads ${TB_NAME}
export TB_NAME

# Test data (optional): empty = testbench defaults in doc/database/input/ and output/
DATA_IN      ?=
DATA_OUT     ?=
SIM_ARGS     ?= $(if $(DATA_IN),+IN=$(DATA_IN)) $(if $(DATA_OUT),+OUT=$(DATA_OUT))

# Coverage: per-test databases <ID>.ucdb of the tests listed in pat.list
COV_TESTS     = $(shell sed '/\/\//d' $(REGRESS_LIST))
COV_DBS       = $(wildcard $(addsuffix .ucdb,$(COV_TESTS)))
COV_MISSING   = $(filter-out $(basename $(COV_DBS)),$(COV_TESTS))

# Schematic (Vivado)
SCH          ?=
PART         ?= xc7a35tcpg236-1
# Vivado: $XILINX_VIVADO (set by settings64.sh), else the newest version found
# in the usual install locations, else PATH.
VIVADO_DIRS  := $(foreach d,$(HOME)/opt/Xilinx /tools/Xilinx /opt/Xilinx, \
                  $(wildcard $(d)/*/Vivado/bin $(d)/Vivado/*/bin))
VIVADO_BIN   ?= $(if $(XILINX_VIVADO),$(XILINX_VIVADO)/bin,$(lastword $(sort $(VIVADO_DIRS))))
VIVADO       := $(if $(VIVADO_BIN),$(VIVADO_BIN)/)vivado

#==============================
# Prerequisites run in the written order (clean_sim first)
.NOTPARALLEL:

all: clean_sim build run

all_wave: clean_sim build run wave

all_cov: clean_sim build_cov run_cov

build:
	mkdir -p log
	cp -rf ../testcases/$(TESTNAME).v run_test.v
	vlib work
	vmap work work
	vlog -f compile.f | tee compile.log
build_cov:
	mkdir -p log
	cp -rf ../testcases/$(TESTNAME).v run_test.v
	vlib work
	vmap work work
	vlog +cover=bcesft -f compile.f
run:
	vsim -debugDB -l $(TESTNAME).log -voptargs=+acc -assertdebug -c $(TB_NAME) $(SIM_ARGS) -do "log -r /*;run -all;"
	cp $(TESTNAME).log ./log
	mv $(TESTNAME).log sim.log
run_cov:
	vsim -coverage -l $(TESTNAME).log -c $(TB_NAME) $(SIM_ARGS) -voptargs="+cover=bcesft" -assertdebug -do "coverage save -onexit $(TESTNAME).ucdb; log -r /*;run -all"
	cp $(TESTNAME).log ./log
	mv $(TESTNAME).log sim.log
	mkdir -p coverage/$(TESTNAME)
	vcover report $(TESTNAME).ucdb -output coverage/$(TESTNAME)/summary_report.txt
	vcover report -zeros -details -code bcesft -annotate -All -codeAll $(TESTNAME).ucdb -output coverage/$(TESTNAME)/detail_report.txt
wave:
	vsim -i -view vsim.wlf -do "add wave vsim:/$(TB_NAME)/*; radix -$(RADIX)" &
schematic:
	mkdir -p log
	$(VIVADO) -mode gui -source schematic.tcl -log log/schematic.log -journal log/schematic.jou \
	  -tclargs $(MODULE) $(PART) $(or $(SCH),.) rtl.f &
gen_data:
	python3 script/$(MODULE)_gen_vectors.py
# Total database IP.ucdb rebuilt from scratch: only the per-test databases of
# pat.list are merged, never the previous IP.ucdb
merge_cov:
	@test -n "$(COV_DBS)" || { echo "No coverage database of pat.list: run make all_cov first"; exit 1; }
	$(if $(COV_MISSING),@echo "Not run with coverage (left out): $(COV_MISSING)")
	rm -f IP.ucdb
	vcover merge IP.ucdb $(COV_DBS)
gen_cov: merge_cov
	mkdir -p coverage
	vcover report IP.ucdb -output coverage/summary_report.txt
	vcover report -zeros -details -code bcesft -annotate -All -codeAll IP.ucdb -output coverage/detail_report.txt
gen_html: merge_cov
	rm -rf covhtmlreport
	vcover report -zeros -details -code bcesft -annotate -testhitdataAll -html IP.ucdb
# Temporary files of one run; keeps coverage data (*.ucdb, coverage/) and log/
clean_sim:
	rm -rf work
	rm -rf vsim.dbg
	rm -rf *.ini
	rm -rf *.log
	rm -rf *.wlf
	rm -rf transcript
	rm -rf run_test.v
# Everything generated, coverage data included (log/ is kept)
clean: clean_sim
	rm -rf *.ucdb
	rm -rf coverage covhtmlreport
	rm -rf .Xil *.jou *.str
help:
	@echo ""
	@echo "****************************************"
	@echo "** make clean     : clean all generated data, coverage included"
	@echo "** make clean_sim : clean temporary files of one run, keep coverage data"
	@echo "** make build     : build the design"
	@echo "** make build_cov : build the design in coverage mode"
	@echo "** make run       : run simulation"
	@echo "** make run_cov   : run simulation in coverage mode + report of this test (coverage/<TESTNAME>/)"
	@echo "** make all       : clean_sim, build and run simulation"
	@echo "** make all_cov   : clean_sim, build and run simulation in coverage mode"
	@echo "** make all_wave  : clean_sim, build and run simulation, then open waveform"
	@echo "** make wave      : open waveform (QuestaSim)"
	@echo "** make schematic : open RTL schematic (Vivado), SCH=<instance> for a sub-block"
	@echo "** make gen_data  : rebuild the test data of MODULE (script/<module>_gen_vectors.py)"
	@echo "** make gen_cov   : rebuild IP.ucdb from the tests of pat.list, total text report (coverage/)"
	@echo "** make gen_html  : rebuild IP.ucdb from the tests of pat.list, total html report (covhtmlreport/)"
	@echo "****************************************"
	@echo ""
