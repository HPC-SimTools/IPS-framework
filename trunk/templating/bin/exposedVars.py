import os,shutil

def getValuesInteractively(attribs,current=None):
  """ Given a dictionary of the values to fill, prompt the user for 
      the new values
  """
  for at in attribs.keys():
      attype = attribs[at]["type"]
      atdefault = attribs[at]["default"]
      if current:
        atcurrent = current[at]
        queryStr = "%s [default=%s, current=%s, type=%s] -> " % ( at, atdefault, atcurrent, attype)
      else:
        queryStr = "%s [default=%s, type=%s] -> " % ( at, atdefault, attype)
      atVal = raw_input(queryStr)
      if not atVal.strip():
        if current:
          attribs[at]["value"]=atcurrent
        else:
          attribs[at]["value"]=atdefault
        continue
      if attype == "double":
        attribs[at]["value"] = float(atVal)
      elif attype == "integer":
        attribs[at]["value"] = int(atVal)
      else:
        attribs[at]["value"] = atVal
  return attribs

def getCurrentValues(fileName):
  """ Parse the current template file and obtain the current values.
      Not the fanciest parser
  """
  mkf=open(fileName,"r")
  currentVals={}
  while 1:
    line=mkf.readline()
    if line.strip().startswith("<") or line.strip().startswith("#") or line.strip().startswith("%>"):
       if "Insert the input file" in line:
         break
       else:
         continue    # Skip commented lines
    elif not line.strip():
         continue    # Skip blank lines
    else:
       # Grab the var, vals here
       var=line.split("=")[0]
       val=line.split("=")[1].strip()
       currentVals[var]=val
  mkf.close()
  return currentVals

def replaceCurrentValues(fileName,newVals):
  """ Parse the current template file and replace the current values
      with new values
      Not the fanciest parser
  """
  mkf=open(fileName,"r")
  if os.path.sep in fileName:
    tempFilename=os.path.join(os.path.dirname(fileName),"temp"+os.path.basename(fileName))
  else:
    tempFilename="temp"+fileName
  tmp=open(tempFilename,"w")
  writeAll=False
  while 1:
    line=mkf.readline()
    if not line: break
    if writeAll:
      tmp.write(line)
    else:
      if line.strip().startswith("<") or line.strip().startswith("#"):
         tmp.write(line)
         if "Insert the input file" in line: writeAll=True
         continue
      elif line.strip().startswith("%>"):
         tmp.write(line)
         continue
      elif not line.strip():
         tmp.write(line)
         continue    # Skip blank lines
      else:
         # Grab the var, vals here
         var=line.split("=")[0].strip()
         newLine=var+"="+str(newVals[var]["value"])+"\n"
         tmp.write(newLine)
  tmp.close()
  mkf.close()
  shutil.move(tempFilename,fileName)
  return 
