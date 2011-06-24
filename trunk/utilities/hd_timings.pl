#!/usr/bin/env perl

#------------------------------------------------------------------------
# Test the speed of writing to a storage location. This uses /dev/zero as
# the source of data to write, and writes to $targetfile. It varies the
# blocksize used for writing to find sorta optimal timings. If $verbose is
# set it prints out everything in a readable way; otherwise it prints out
# a single row of header info and then each timing row by row.  The header
# has a % in the first column so it will be a Matlab comment. Printing 
# is to $resultsfile since invariably I want to keep the timings.
#
# To use, edit the filesize, targetfile, and resultfile variables.
#
#   Randall Bramley
#   Department of Computer Science
#   Indiana University
#   Bloomington, IN 47405
#   bramley@cs.indiana.edu
#   Thu Oct 27 16:36:33 EST 2005
#------------------------------------------------------------------------

use Time::HiRes qw(gettimeofday);
use Sys::Hostname;

#----------------------------------------------
# File size of 256 Mbytes, for standard systems
#----------------------------------------------
$filesize = 268435456;
#----------------------------------------------
# File size of 2 Gbytes, for larger SANs
#----------------------------------------------
# $filesize = 2147483648;
$targetfile = "/home/elwasif/zeds";
$resultsfile = "/home/elwasif/HD_timings";

$machine = hostname();

$verbose = 0;
open resultsfile, ">>$resultsfile" or die "Could not open $resultsfile in append mode\n";
print resultsfile "% Results from $machine writing to $targetfile\n";

if (!$verbose) {
    print resultsfile "% bs\t", "count\t", "elapsed\t\t", "Mbs\n" ;
}

@blocksizes = (2048, 4096, 8192, 16384, 32768);
foreach $bs (@blocksizes) {
    $count = $filesize/$bs;
    system("rm -f $targetfile");
    if ($verbose){
        print resultsfile "Blocksize ", $bs, " number of blocks = ", $count, "\n"
    };

    $t0 = gettimeofday();
    system("dd if=/dev/zero of=$targetfile bs=$bs count=$count >& /dev/null");
    $t1 = gettimeofday();
    $elapsed = $t1 - $t0;
    $Mbs = (1.0e-6*$filesize)/$elapsed;

    if ($verbose) {
        print resultsfile "Elapsed time: ", $elapsed, " seconds \n" ;
        print resultsfile "Transfer rate: ", $Mbs, " Mbyte/second \n" ;
        print resultsfile "--------------------------------------------\n\n" ;
    }
    else {
        printf resultsfile "%d\t%d\t%9.6f\t%9.6f\n",$bs, $count, $elapsed, $Mbs ;
    }
}
print resultsfile "%--------------------------------------------\n\n" ;

#---------------------
# Clean up target file
#---------------------
system("rm -f $targetfile");
