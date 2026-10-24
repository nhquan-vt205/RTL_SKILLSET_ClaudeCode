# ============================================================================
# schematic.tcl - Vivado RTL elaboration + schematic of the module under test
# Called by "make schematic" from sim/:
#   vivado -mode gui -source schematic.tcl -tclargs <top> <part> <sch|.> <rtl.f>
# <sch> ".": top level of <top>; else an instance path under it, e.g. u_ctrl.
# ============================================================================
lassign $argv top part sch flist

set files {}
set fp [open $flist r]
foreach f [split [read $fp] "\n"] {
  set f [string trim $f]
  if {$f ne "" && ![string match "//*" $f]} { lappend files [file normalize $f] }
}
close $fp

create_project -in_memory -part $part
read_verilog $files
synth_design -rtl -top $top -name rtl_1

if {$sch eq "."} {
  show_schematic -name $top [concat [get_cells] [get_ports] [get_nets]]
} else {
  show_schematic -name $sch [concat [get_cells $sch/*] [get_pins $sch/*] [get_nets $sch/*]]
}
