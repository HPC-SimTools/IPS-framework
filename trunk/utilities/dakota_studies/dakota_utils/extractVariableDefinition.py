#! /usr/bin/env python

# This script is an integral part of executing a parameter study with dakota and ips
# It performs the following function:
# 1) Searches the given file for the first definition of the given variable name
# Usage
#  ./extractVariableDefinition.py [TARGET FILE] [VARIABLE NAME]
#   TARGET FILE
#       the file to search for the variable definition
#   VARIABLE NAME
#       name of the variable definition to search for

import sys
import os

def extract_variable_definition(line, varName):
  """ Attempts to extract the definition of the given variable name from the given line """
  # slice the line at the first equals sign (empty string if no equals sign)
  slicedLine = line[0:line.find("=")]

  # Now look for the variable name
  nameLocation = slicedLine.find(varName)
  if nameLocation == -1:
    return None

  # is this line commented?
  poundLocation = slicedLine.find("#")
  if -1 != poundLocation < nameLocation:
    return None

  return line[line.find("=")+1:]

def main():
  # Check for correct number of arguments
  if len(sys.argv) != 3:
    print """Incorrect number of arguments, expected 2.
          Usage:
              extractVariableDefinition [TARGET FILE] [VARIABLE NAME]
    """
    sys.exit()

  # Try to open file named in first argument
  try:
    inputFile = open(sys.argv[1], 'r')
  except:
    print "Error while trying to open input file ", sys.argv[1]
    raise

  for line in inputFile:
    # Does the line contain a definition of the requested variable?
      definition = extract_variable_definition(line, sys.argv[2])
      if definition != None:
        definition = definition[:definition.find("#")].strip()
        print definition
        inputFile.close()
        sys.exit()

  inputFile.close()

main()
