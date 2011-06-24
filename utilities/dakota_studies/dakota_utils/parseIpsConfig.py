#! /usr/bin/env python

# This script is an integral part of executing a parameter study with dakota and ips
# It performs the following function:
# 1) Replaces the definition of SIM_ROOT in the ips config file

import sys
import os

def extract_variable_definition(line, varName):
  """ Returns true if the given line contains a definition for the given variable """
  # slice the line at the first equals sign (empty string if no equals sign)
  slicedLine = line[0:line.find("=")]

  # Now look for the variable name
  nameLocation = slicedLine.find(varName)
  if nameLocation == -1:
    return None

  # is this line already commented?
  poundLocation = slicedLine.find("#")
  if -1 != poundLocation < nameLocation:
    return None

  return line[line.find("=")+1:]

def main():
  # Check for proper number of arguments
  if len(sys.argv) != 4:
    print """Incorrect number of arguments, expected 3.
          Usage:
              ./parseIpsConfig.py [NEW DEFINITION OF SIM_ROOT] [INPUT IPS CONFIG] [OUTPUT IPS CONFIG]
    """
    sys.exit()
  if sys.argv[2] == sys.argv[3]:
    print "Error: input and output files must not be the same."
    sys.exit()

  # Copy the arguments to meaningful variables
  NEW_DEFINITION = sys.argv[1]
  INPUT_IPS_CONFIG = sys.argv[2]
  OUTPUT_IPS_CONFIG = sys.argv[3]

  # Try to open input file for reading
  try:
    inputFile = open(INPUT_IPS_CONFIG, 'r')
  except:
    print "Error while trying to open input file ", INPUT_IPS_CONFIG
    raise

  # Try to open output file (for writing)
  try:
    outputFile = open(OUTPUT_IPS_CONFIG, 'w')
  except:
    print "Error while trying to open output file ", OUTPUT_IPS_CONFIG
    inputFile.close()
    raise

  # Ok, let's do it
  # for each line in the input file
  #    if the line contains the definition of SIM_ROOT, comment it out
  #        and follow it with our new definition
  #    otherwise write it to the output file as is
  for line in inputFile:
    # Does the line contain a definition of SIM_ROOT?
    if extract_variable_definition(line, "SIM_ROOT") != None:
      outputFile.write("SIM_ROOT = " + NEW_DEFINITION + "\n")
      line = "#" + line

    # Write the line to the file (possibly with an added #)
    outputFile.write(line)

  inputFile.close()
  outputFile.close()

main()
