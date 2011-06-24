#! /usr/bin/env python

# This script is an integral part of executing a parameter study with dakota and ips
# It performs the following function:
#    Reads the name/value pairs of the values to be used in the parameter study,
#    and constructs an input namelist for this exact run of IPS

import sys

def process_line(line, vars):
    for var in vars:
        varLocation = line.find(var[0])
        if varLocation != -1:
            equalsLocation = line.find("=")
            if equalsLocation > varLocation:
                print "Changing line [", line, "] to [", var[0] + " = " + var[1] + ",\n]"
                return var[0] + " = " + var[1] + ",\n"
    return line

def main():
  # Validate input (as possible)
  if len(sys.argv) != 4:
      print """Incorrect number of arguments, expected 3
               Usage:
                 ./createNamelist.py [PARAMETER_INPUT_FILE] [INPUT_NAMELIST_FILE] [OUTPUT_NAMELIST_FILE]
            """
      sys.exit()
  if sys.argv[2] == sys.argv[3]:
      print "Incorrect usage: input and output namelist files must not have the same name:",sys.argv[3]
      sys.exit()

  # First task: open dakota parameter file and create a list of variable names and values
  DAKOTA_RESERVED_WORDS = ["DAKOTA_VARS", "DAKOTA_FNS", "ASV_1", "DAKOTA_DER_VARS", "DVV_1", "DAKOTA_AN_COMPS"]
  print "Processing parameter file: ", sys.argv[1]
  vars = []
  try:
      parameterFile = open(sys.argv[1], 'r')
  except:
      print "Error opening parameter file: ", sys.argv[1]
      raise
  for line in parameterFile:
      # each line has the form " { var = 1 } "
      # remove the {, =, and }
      strippedLine = line.replace("{", " ").replace("=", " ").replace("}", " ")
      tokens = strippedLine.split()
      if tokens[0] in DAKOTA_RESERVED_WORDS:
        print "Ignoring dakota reserved word: ", tokens[0]
      else:
        vars.append( (tokens[0], tokens[1]) )
  print "Found these variable/value pairs: ", vars
  parameterFile.close()

  # Second task: open namelist file
  #   for each line in namelist
  #     if line contains variable definition,
  #        replace line with dprepro expression
  #   eg. replace "x = 3"
  #       with "x = {x}"
  try:
      namelistFile = open(sys.argv[2], 'r')
  except:
      print "Error opening input namelist file: ", sys.argv[2]
      raise
     
  try:
      namelistTemp = open(sys.argv[3], 'w')
  except:
      print "Error opening output namelist file: ", sys.argv[3]
      namelistFile.close()
      raise


  for line in namelistFile:
      namelistTemp.write(process_line(line, vars))

  namelistFile.close()
  namelistTemp.close()

main()
