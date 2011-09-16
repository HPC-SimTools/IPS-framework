#!/bin/sh

#---------------------------------------------------
# This shows interactive/gui usage which is what
# Ammar was really demonstrating.  
#---------------------------------------------------

#---------------------------------------------------
#  First do interactive use.  Note that specifying 
#  the gui file puts one into interactive use
#---------------------------------------------------
bin/parseMako.py -i simple02/euler1d-input.mko -g simple02/euler1d-input.czgui

#-------------------------------------------------------------
#  This combines interactive use with some runspace setup
#-------------------------------------------------------------
bin/parseMako.py -i simple02/euler1d-input.mko -g simple02/euler1d-input.czgui -n simple03

#-------------------------------------------------------------
#  This is like doing things by hand.
#  You can think of this as using mako as a txpp.py replacement
#-------------------------------------------------------------
cp -a simple03 simple04
cd simple04
rm -f *.in *.czgui
if test -n $EDITOR; then
  $EDITOR euler1d-input.mko
else
  vi euler1d-input.mko
fi
bin/parseMako.py -i euler1d-input.mko 
