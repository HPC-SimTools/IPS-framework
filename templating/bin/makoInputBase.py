import xml.dom.minidom
# impoer mako stuff
from mako.template import Template
from mako.runtime import Context
from StringIO import StringIO
import os

def ctkguiGetAttribs(fileName):
  """ Given a file specifying the GUI elements, return a dictionary of
      those values filled with the defaults
  """
  data = open(fileName).read()
  dom = xml.dom.minidom.parseString(data)
  attribs = {}
  # get all attributes
  attribTags = dom.getElementsByTagName("Attrib")
  for at in attribTags:
      atkey = at.getAttribute("key")
      attype = at.getAttribute("type")    
      attribs[atkey] = {}
      atdefault = at.getAttribute("default")
      attribs[atkey]["type"] = attype
      # Put the default values into values to start off
      if attype == "double":
        attribs[atkey]["default"] = float(atdefault)
        attribs[atkey]["value"]  = float(atdefault)
      elif attype == "integer":
        attribs[atkey]["default"] = int(atdefault)
        attribs[atkey]["value"]  = int(atdefault)
      else:
        attribs[atkey]["default"] = atdefault
        attribs[atkey]["value"]  = atdefault
  return attribs

def renderTemplateAmmar(fileName,attribs):
  data = open(fileName).read()
  dom = xml.dom.minidom.parseString(data)
  tmplStr = ""
  # now read in template
  tmplNode = dom.getElementsByTagName("template")
  for n in tmplNode[0].childNodes:
      if n.nodeType == n.CDATA_SECTION_NODE:
          tmplStr = n.data

  # Make a dictionary of just values
  attribValues={}
  for at in attribs.keys():
    attribValues[at]=attribs[at]['value']
  # create Mako object
  tmpl = Template(tmplStr)
  buf = StringIO()
  ctx = Context(buf, data=attribValues)
  tmpl.render_context(ctx)
  inFile=os.path.splitext(fileName)[0]+'.in'
  inf=open(inFile,"w")
  inf.write(buf.getvalue())
  inf.close()
  #print buf.getvalue()
  return


def renderTemplate(fileName):
  myTemplate = Template(filename=fileName)
  # create Mako object
  inFile=os.path.splitext(fileName)[0]+'.in'
  inf=open(inFile,"w")
  inf.write(myTemplate.render())
  inf.close()
  return
