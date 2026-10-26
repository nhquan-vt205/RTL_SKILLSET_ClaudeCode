# Coverage exclusions of the project, kept in exclude.do (sim/).
# Sourced by the Makefile on the total database IP.ucdb only (vsim -viewcov in
# merge_cov and cov_gui); per-test databases carry no exclusions.
#   excl_load      apply exclude.do if it exists
#   excl_save      write every current exclusion (with its comment) to exclude.do
#   excl_autosave  call excl_save when vsim quits (window close or "quit")
# exclude.do holds "coverage exclude ..." commands with paths relative to sim/.

set excl_file   exclude.do
set excl_failed 0

proc excl_load {} {
  global excl_file excl_failed
  if {![file exists $excl_file]} {
    return
  }
  if {[catch {do $excl_file} msg]} {
    set excl_failed 1
    echo "** Warning: $excl_file not fully applied ($msg); autosave disabled"
  } else {
    echo "Coverage exclusions applied from $excl_file"
  }
}

proc excl_save {} {
  global excl_file
  set tmp "$excl_file.tmp"
  file delete -force $tmp
  coverage report -excluded -file $tmp
  set body ""
  if {[file exists $tmp]} {
    set fh [open $tmp r]
    set body [read $fh]
    close $fh
    file delete -force $tmp
  }
  # Absolute paths of this sim/ directory -> relative (portable across clones)
  set body [string map [list "[pwd]/" ""] $body]
  set fh [open $excl_file w]
  puts $fh "# Coverage exclusions, written by excl_save (cov_excl.tcl)."
  puts $fh "# Edit the exclusions in the coverage GUI (make cov_gui), not by hand."
  puts -nonewline $fh $body
  close $fh
  echo "Coverage exclusions saved to $excl_file"
}

proc excl_on_quit {args} {
  global excl_failed excl_file
  if {$excl_failed} {
    echo "** Warning: $excl_file was not fully applied, not overwritten"
    return
  }
  excl_save
}

proc excl_autosave {} {
  trace add execution quit enter excl_on_quit
}
