import xml.dom.minidom
# impoer mako stuff
from mako.template import Template
from mako.runtime import Context
from StringIO import StringIO

fileName = "euler1d-input.xml"
# read and parse file
data = open(fileName).read()
dom = xml.dom.minidom.parseString(data)

attribs = {}
# get all attributes
attribTags = dom.getElementsByTagName("Attrib")
for at in attribTags:
    atkey = at.getAttribute("key")
    attype = at.getAttribute("type")    
    queryStr = "%s [%s] -> " % ( atkey, attype)
    atVal = raw_input(queryStr)
    if attype == "double":
        attribs[atkey] = float(atVal)
    elif attype == "integer":
        attribs[atkey] = int(atVal)
    else:
        attribs[atkey] = atVal

tmplStr = ""
# now read in template
tmplNode = dom.getElementsByTagName("template")
for n in tmplNode[0].childNodes:
    if n.nodeType == n.CDATA_SECTION_NODE:
        tmplStr = n.data

# create Mako object
tmpl = Template(tmplStr)
buf = StringIO()
ctx = Context(buf, data=attribs)
tmpl.render_context(ctx)
print buf.getvalue()

