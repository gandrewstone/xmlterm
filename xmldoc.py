import sys, time, types
import math, os, re, string
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape,unescape
import threading
import pdb
import mainliner
import wx

class DocElem:
  """An element (one xml tag) in the document"""
  def __init__(self,elem,panel=None, size=None, pos=None):
    self.elem = elem
    self.panel = panel
    self.size = size
    self.pos = pos

def findFirstTagOf(s,lst):
  tmp =  s.find("<")
  if tmp == -1: return -1
  for l in lst:
    if s[tmp:].startswith(l):
      return tmp
  return -1

class DirtyXmlReadable():
  def __init__(self,fd,nonXmlChunkCallback,topLevelTags):
    self.fd = fd
    self.prefix = "<top>"
    self.suffix = "</top>"
    self.nonXmlChunkCallback = nonXmlChunkCallback
    self.inXML = False
    self.inject = None
    self.topLevelTags = topLevelTags
    # self.docToDate = open("out.txt","w")

  def rawread(self,maxSize):
    """Read at most maxSize bytes from the stream, no XML foolishness"""
    ret = ""
    if self.inject:
      ret = self.inject[0:maxSize]
      self.inject = self.inject[maxSize:]
      maxSize -= len(ret)
    if maxSize:
      ret += os.read(self.fd,maxSize)
    return ret

  def read(self,maxSize):
    # pdb.set_trace()
    if self.prefix:
      t = self.prefix
      self.prefix = None
      return t
 
    while 1:
      try:
        if self.inject:  # Push some text in from external source or that we deferred from a prior read.
          next=self.inject
          self.inject = None
        else: next = os.read(self.fd,maxSize)

        if next:
          #if self.docToDate:   # Debugging dump the document
          #    self.docToDate.write(next)
          #    self.docToDate.flush()

          # I need an incremental and error tolerant XML parser (beautifulsoup?), but for now we'll try to test for stuff
          if self.inXML:
            gt = next.find(">") 
            if gt != -1: # split across the end so we have the opportunity to close out the top level XML and grab some nonXML data
              self.inject = next[gt+1:]
              next = next[0:gt+1]
          else:
            nonXML = None
            pos = findFirstTagOf(next, self.topLevelTags)
            if pos==-1: # its all nonXML
              nonXML = next
              next = None
            else:
              # I'll set this to true in the XML start callback: self.inXML = True
              nonXML = next[0:pos]
              next = next[pos:]

              gt = next.find(">") 
              if gt != -1: # split across the end so we have the opportunity to close out the top level XML and grab some nonXML data
                self.inject = next[gt+1:]
                next = next[0:gt+1]
            if nonXML: self.nonXmlChunkCallback(nonXML)
          # print "received [%s]" % next
          if next: 
            # debugging if 0: # self.docToDate: 
            #  self.docToDate.write(next)
            #  self.docToDate.flush()
            return next
      except OSError, e:
        t = self.suffix
        self.suffix = ""  # As per def of read function this denotes end of file
        return t
      else:
        time.sleep(.1)  # read should block but if it does not spin loop

class Selection:
  def __init__(self, doc, startPos, idx, startPanel):
    self.doc   = doc
    self.startPos = startPos
    self.start = (startPanel, idx)
    self.end = (startPanel,idx)

  def simpleString(self):
    """Returns the context of this panel as a string with no markup"""
    ret  = []
    if self.start[1] is not None:
      i = self.start[1]
      while i <= self.end[1]:  # Turn off anything that was selected
        s = self.doc.doc[i].panel.simpleString()
        if s: ret.append(s)
        i+=1
    return("\n".join(ret))

  def complete(self):
    if self.start[1] is not None:
      i = self.start[1]
      while i <= self.end[1]:  # Turn off anything that was selected
        self.doc.doc[i].panel.setSelected(False)
        i+=1

  def endAt(self,panel,idx,pos):
      i = idx+1 
      while i <= self.end[1]:  # Turn off anything that was selected
        self.doc.doc[i].panel.setSelected(False)
        i+=1
      i = self.end[1]
      while i <= idx:  # Turn on any new selections
        self.doc.doc[i].panel.setSelected(True)
        i+=1
      self.end=(panel,idx)

class Document:
  def __init__(self,resolver,changeCallback=None):
    self.doc=[DocElem(None,None,(0,0),(0,0))]  # Starter element
    self.resolver=resolver  # How strings or ElementTrees are turned into GUI
    self.lastLaid = 0       # All items before this index are properly positioned on the virtual document 
    self.bottom = 0         # The Y bottom of the virtual document (in pixels)
    self.spacer=(0,0)       # How much space to put between GUI panels
    self.pending=[]
    self.callOnChange=changeCallback  # When the document or children change, I will call this function
    self.widgets = {}       # a dictionary of name widgets, used for widget updates or replacement

  def simpleString(self):
    """Returns the context of this panel as a string with no markup"""
    ret  = []
    for d in self.doc:
        if d.panel: 
          s = d.panel.simpleString()
          if s: ret.append(s)
    return("\n".join(ret))

  def remove(self,win):
    """Remove this window from the document.  The data is left there so the window can be re-created if needed"""
    i = -1
    for doce in self.doc:
      i+=1
      if doce.panel == win:
        doce.panel=None
        doce.size = (0,0)
        self.layout(i-1)
        if self.callOnChange: self.callOnChange()
        if doce.elem is not None and doce.elem.tag == "widget" and doce.elem.attrib.has_key("name"):
          del self.widgets[doce.elem.attrib["name"]]

  def getWindow(self,pos):
    """Get the window that contains the passed position.  Returns (window, posInDoc, pointer offset in window) or (None,None,None)"""
    count = -1
    for doce in self.doc:  # TODO switch to binary search
      count += 1
      if pos[0] >= doce.pos[0] and pos[1] >= doce.pos[1]:
        offset = (pos[0] - doce.pos[0], pos[1] - doce.pos[1])
        if offset[0] <= doce.size[0] and offset[1] <= doce.size[1]:
          return (doce.panel, count, offset)
    return (None,None, None)
        

  def startSelection(self,pos):
    """Start selecting at the passed position in the document.  Return an object that tracks what is selected"""
    (panel, idx, offset) = self.getWindow(pos)
    sel = Selection(self,pos,idx,panel)
    if panel:
      print "selected %d" % idx
      panel.setSelected(True)
    return sel

  def continueSelection(self,pos,selection):
    """continue selecting at the passed position in the document.  Update the passed selection object"""
    (panel, idx, offset) = self.getWindow(pos)
    if panel: selection.endAt(panel,idx, offset)


  def rediscoverSizes(self,panelLst):
    firstChange = 0
    i = -1
    for doce in self.doc:
      i+=1
      if doce.panel in panelLst:
        doce.size = doce.panel.GetSize().Get()
        if firstChange == 0: firstChange = i
    
    return firstChange-1

  def nonXML(self,data):

    def doit(data):
      end = self.doc[-1]
      newpanel = False
      # debugging: prints the ascii of everything read in: print [ord(x) for x in list(data)]
      try: # Try to add the nonxml onto the end. if anything goes wrong (like panel does not have the API) then create a new one
        end.panel.appendText(data)
      except AttributeError, e:  
        self.append(data)
        newpanel = True
      if not newpanel:
        end.size = end.panel.calcSize()
        self.lastLaid = len(self.doc)-2 # before the end panel that I just changed
      if self.callOnChange: self.callOnChange()
 
    wx.PostEvent(self.resolver.parentWin,mainliner.ExecuteEvent(lambda d=data:doit(d)))

  def feedProcessor(self,fd):
    """This runs in a separate thread so NO GUI calls!"""
    topLevelTags = []
    for tg in self.resolver.tags.keys():
      topLevelTags.append("<" + tg)
    dxr = DirtyXmlReadable(fd, self.nonXML,topLevelTags)
    # get an iterable
    context = ET.iterparse(dxr, events=("start", "end"))
    # turn it into an iterator
    context = iter(context)
    # get the root element
    event, root = context.next()

    enclosingXML = None

    bdata = []
    for event, elem in context:
      if event == "start":
        print "starting %s" % elem.tag
        if elem.tag.startswith("bdata"):  # Special case the "bdata" tag -- BINARY DATA -- it breaks XML.  The tag can be bdataANYTHING -- this allows a unique tag whose closer can be found in the output string.
          #pdb.set_trace()
          bdataLen = None
          if elem.attrib.has_key("length"):  # If it has a length attribute just read that many bytes in
            bdataLen = int(elem.attrib["length"])
            while bdataLen:  # Read this size of binary data
              data = dxr.rawread(bdataLen)
              if not data:  # End of file
                break
              bdata.append(data)
              bdataLen -= len(data)
          else:  # TODO read until you find "</" + elemtag + ">", and "jam" that closer back into the dxr
            assert(0)  
        if not dxr.inXML:
          dxr.inXML = True
          enclosingXML=elem
          #print "enclosing ", repr(elem), str(elem)
      if event == "end":
        #print "completed %s enclosing %s" % (elem.tag,repr(elem))
        if bdata:  # Since the inside of bdata is "raw" (unparsed) data, we KNOW the end event happens just after the start
          elem.data = "".join(bdata)
          elem.text = elem.data  # Will overwriting ET's text field mess something up?
          bdata=[]
        if elem == enclosingXML:
          dxr.inXML = False
          enclosingXML = None
          wx.PostEvent(self.resolver.parentWin, mainliner.ExecuteEvent(lambda a=self,b=elem: a.append(b)))
          # TODO: Right now I wait for the entire enclosing (top level) XML to come, but in the future I should not do so, so programs can update more dynamically
      
    #print "feed is complete!"
    pass

  def GetSize(self):
    """Returns the size in pixels of this document"""
    doce = self.doc[-1]
    return (doce.pos[0]+doce.size[0],doce.pos[1]+doce.size[1])

  def startFeed(self,fd):
    """start providing data to this document from a file descriptor"""
    self.feedThread = threading.Thread(group=None, target=lambda x=fd:self.feedProcessor(x), name="XmlFeeder")
    self.feedThread.daemon = True  # don't stop the shell from quitting
    self.feedThread.start()


  def append(self,doc):
    if type(doc) == types.ListType:
      for d in doc: self.append(d)
      return
    if type(doc) in types.StringTypes:
      try:
        et = ET.fromstring(doc)
      except ET.ParseError:
        et = ET.fromstring("<text>" + escape(doc) + "</text>")
    else: # Its already an ET element
      et = doc
    self.resolver.windows=[]
    self.resolver.resolve(et)
    # assert(len(self.resolver.windows)==1)
    for win in self.resolver.windows:
      sz = win.GetBestSizeTuple()
      sz2 = win.GetSize()

      # If its an existing named widget, do a replacement (or TDB merge)
      if et.tag == 'widget' and et.attrib.has_key("name") and self.widgets.has_key(et.attrib["name"]):
        doce = self.widgets[et.attrib["name"]]
        oldwin = doce.panel
        oldwin.Hide()
        oldwin.Destroy()
        doce.elem = et
        doce.panel = win
        doce.size = sz
        doce.pos = None
        self.lastLaid = 0  # I don't know where this widget is so I have to search the entire doc
      else:  # Its a new widget
        doce = DocElem(et,win, sz,None)  
        if et.tag == 'widget' and et.attrib.has_key("name"):
          self.widgets[et.attrib["name"]] = doce
        self.doc.append(doce)

      if win and self.callOnChange: self.callOnChange()  # Tell registrant that something changed in the document
    return

    
  def layout(self,pos=None):
    if pos is None:
      i = self.lastLaid
    else:
      i = pos
    if i<0: i=0
    curx = 0 # no horizontal layout now self.doc[i].psp[2][0]
    cury = self.doc[i].pos[1]+self.doc[i].size[1]  
    i += 1
    while i<len(self.doc):
      doce = self.doc[i]
      doce.pos = (curx, cury)
      # print i, doce.__dict__
      cury += doce.size[1]+self.spacer[1] # Move down
      i += 1
    self.bottom = cury

  def position(self,start=(0,0),size=None):  # Position is already calculated from the top so just need to move it
    maxx=0
    maxy=0
    for doce in self.doc:
      if doce.panel: 
# is the bottom of the panel below the top of the screen?  and is the top of the panel above the bottom of the screen?
        if (doce.pos[1]+doce.size[1] >= start[1]) and (size is None or doce.pos[1] <= start[1]+size[1]):  
             doce.panel.MoveXY(doce.pos[0] - start[0] ,doce.pos[1] - start[1])
             doce.panel.Show(True)
        else:
          doce.panel.Show(False)
      maxx= max(maxx, doce.size[0]+doce.pos[0])
      maxy= max(maxy, doce.size[1]+doce.pos[1])
    return (maxx,maxy)

  def positionFromBottom(self, size):
    sizey = size[1]
    i = len(self.doc)
    difference = self.bottom - sizey  
    while i>0:  # Go thru the windows from bottom to top, moving them properly
      i -= 1
      doce = self.doc[i]
      pos = doce.pos
      y = pos[1]-difference
      if doce.panel: 
        doce.panel.MoveXY(pos[0],y)
        doce.panel.Show(True)
      if y<=0: # No windows above this are visible
        break
    while i>0:
      i -= 1
      if self.doc[i].panel: self.doc[i].panel.Show(False)
