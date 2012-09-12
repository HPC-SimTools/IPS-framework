#!/bin/bash
#------------------------------------------------------------------
#  Yes, you can think of almost everything as a function, 
#  but this may upset your wife.
#		-- Larry Wall
#------------------------------------------------------------------
# global_funcs.sh
#  Various useful functions to use in nimrod management scripts
#  Functions for modifying files
#	 replace_line 
#  Functions for file management:
#	 link_file
#	 copy_file
#	 make_version_bindir
#------------------------------------------------------------------
#topscriptdir=`dirname $0`
source global_library.sh
#------------------------------------------------------------------
# Global vars
#------------------------------------------------------------------
LN_S='ln -s'

#------------------------------------------------------------------
# Replaces a line denoted by keyword with a newline
#------------------------------------------------------------------
function replace_line ()
{
	file="$1"
	keyword="$2"
	new_line="$3"

	# Stuff above keyword line
	# Something like this might work better
	# head -n`grep -n EDITOR .cshrc | cut -f1 -d:` .cshrc
	sed '1!G;h;$!d' $file  \
		| sed -n "/$keyword"'/,$p' \
		| sed -n "/$keyword"'/!p'  \
		| sed '1!G;h;$!d' \
		> tmp_replace_line
	
	echo $new_line >> tmp_replace_line
	
	# Stuff below keyword line
	sed -n "/$keyword"'/,$p' $file \
		| sed -n "/$keyword"'/!p' \
		>> tmp_replace_line

	mv tmp_replace_line $file
}

#------------------------------------------------------------------
# Safe linking
#------------------------------------------------------------------
function link_file
{
	existingfile=`basename $1`
	if [ -e $existingfile ]; then rm $existingfile; fi
	if [ -e $1 ]; then $LN_S $1 .;  fi
}

#------------------------------------------------------------------
# Safe copying
#------------------------------------------------------------------
function copy_file
{
	if test -n $2; then
		if [ -e $1 ]; then cp $1 $2;  fi
	else
		if [ -e $1 ]; then cp $1 .;  fi
	fi
}


