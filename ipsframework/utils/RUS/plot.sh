#!/bin/sh
gnuplot << EOF

set xrange [0:*]
set xtics 100
set xlabel "Time"

set yrange [0:120]
set ylabel "Utilization"

set grid x
set grid y

set terminal pdf dashed fsize 10 color
set output "plots/$1.pdf"

set boxwidth 10

#plot x=100  #lc 2 ls 2
plot "rwfile.$1"  using 1:2 title "Usage" with lines lc 1 lw 5

EOF
