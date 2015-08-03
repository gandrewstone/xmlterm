# TODO: 
# 1. define object with params & instantiate
# 2. Advanced widget manipulation
#   2a. use widget name to identify it.  If same name, default action is to replace existing widget
#   2b. Also based on a flag you can merge new widget data with old
# 3. Widget reference by name
# 4. Widget copy by name 

# 5. Add <input prompt="" completion="{nested dictionary}"/> XML tag which lets you
# 6. text font control
# 7. change text attributes within the same panel: <text size="10">foo<t size="20">BIG</t></text>
# 8. add <span> element that arranges things horizontally, and <div> to arrange vertically, and <grid> to force both vertical and horizontal alignment <span><div><A/><B/></div><div><C/><D/></div></span> becomes:
#     A | C  (| is not shown)
#     B | D
# 9. Add table element to create a sortable nested table of items
# 10. In ProcessPanel and XmlShell, merge output text into one stream and then pick off XML tags when they appear complete
#     try /bin/bash: cat smiley.svg
#     XMLTerm> echo "<widget><display>"; cat smiley.svg; echo "</display></widget>"

import sys, time, types
import math
import os
import re
import string
import pdb
import urlparse
import urllib
import svg
from string import Template
import subprocess
import mainliner

from xml.sax.saxutils import escape,unescape

import xml.etree.ElementTree as ET

import wx.lib.scrolledpanel as scrolled
import wx.gizmos as gizmos
#import wx.richtext
#import wx.lib.fancytext
import wx
import wx.aui

BorderStyle=wx.SIMPLE_BORDER #wx.NO_BORDER

from xmlpanels import *
from xmlcmdline import *
from xmldoc import *



def timeHandler(elem,resolver):
  """Create a representation of the 'time' XML tag"""
  w=TimePanel(resolver.parentWin)
  resolver.add(w)

def listHandler(elem,resolver):
  """Create a representation of the 'list' XML tag"""
  w=ListPanel(resolver.parentWin,elem)
  resolver.add(w)

ext2type = { ".bmp": wx.BITMAP_TYPE_BMP, ".gif": wx.BITMAP_TYPE_GIF, ".png":wx.BITMAP_TYPE_PNG, ".jpg":wx.BITMAP_TYPE_JPEG,".jpeg":wx.BITMAP_TYPE_JPEG}

def imageHandler(elem,resolver):
  """Create a representation of the 'img' XML tag"""
  url =  elem.attrib.get('href',None)
  wxBmp = None
  if url:
      path = urlparse.urlparse(url).path
      ext = os.path.splitext(path)[1]
      imType = ext2type[ext]
      handle = urllib.urlopen(url)
      im = wx.ImageFromStream(handle, type=imType, index=-1)
      wxBmp = im.ConvertToBitmap()
      handle.close()
  w = wx.StaticBitmap(resolver.parentWin, -1, wxBmp)
  resolver.add(w)

def textHandler(elem,resolver):
  """Create a graphical representation of the XML 'text' tag"""
  if elem.text:
    size = elem.attrib.get("size",None)
    if size: size = int(size)
    fore = elem.attrib.get("fore",None)
    if fore: fore = color.rgb(fore) # [ int(x) for x in fore.split(",")]
    back = elem.attrib.get("back",None)
    if back: back = color.rgb(back) # [ int(x) for x in back.split(",")]
    w = FancyText(resolver.parentWin,elem.text,fore=fore, back=back,size=size)
    resolver.add(w)

def svgHandler(elem, resolver):
  """Create a graphical representation of the XML 'svg' tag"""
  # pdb.set_trace()
  w = SvgPanel(resolver.parentWin, elem)
  resolver.add(w) 

def plotHandler(elem, resolver):
  """Create a graphical representation of the XML 'plot' tag"""
  w = PlotPanel(resolver.parentWin, elem)
  resolver.add(w) 

def widgetHandler(elem, resolver):
  """Create a graphical representation of the XML 'widget' tag.  A widget is a wrapper around a group of other entities that can be manipulated as a unit by the terminal"""
  r = XmlResolver()
  r.tags=resolver.tags # reference the main resolver dictionary in this subresolver
  w = WidgetPanel(resolver.parentWin, elem,r)
  resolver.add(w) 

def processHandler(elem, resolver):
  """create a GUI for the 'process' tag.  This will actually execute the specified process and pipe input/output between this program and the process"""  
  r = XmlResolver()
  r.tags=resolver.tags # reference the main resolver dictionary in this subresolver
  w = ProcessPanel(resolver.parentWin, elem,r)
  resolver.add(w) 


def defaultHandler(elem,resolver):
  """Handle normal text and any XML that does not have a handler"""
  if elem.text and elem.text.strip():
    w = wx.StaticText(resolver.parentWin,-1,elem.text)
    resolver.add(w) # ,0,wx.ALL | wx.EXPAND,0)
  for child in elem:
    resolver.resolve(child)
    if child.tail and child.tail.strip():
      w = wx.StaticText(resolver.parentWin,-1,child.tail,style = wx.BORDER_NONE)
      resolver.add(w) # ,0,wx.ALL | wx.EXPAND,0)
   

class XmlResolver:
  """This class turns an XML ElementTree representation into GUI widgets"""
  def __init__(self):
    self.tags = {}
    self.sizer = None
    self.parentWin = None
    self.windows=[]
    self.permanentWindows=[]
    self.defaultHandler = defaultHandler

  def clear(self):
    for w in self.windows:
      w.Destroy()
    self.windows = []

  def add(self,window):
    window.Fit()
    self.windows.append(window)

  def getWindow(x,y):
    for w in self.windows:
      winRect = w.GetRect()


  def xxxforwardResizableLayout(self):
    """Place the child windows appropriately within the parent window.  This layout moves from top to bottom and resized the parent to fit the children"""
    curx = 0
    cury = 0
    for lst in [self.windows, self.permanentWindows]:
      for w in lst:
        w.MoveXY(curx, cury)
        (x,y) = w.GetBestSizeTuple()
        cury += y
    self.parentWin.Fit()

  def xxxforwardLayout(self):
    """Place the child windows appropriately within the parent window.  This layout moves from top to bottom and resized the parent to fit the children"""
    maxx = curx = 0
    maxy = cury = 0
    for lst in [self.windows, self.permanentWindows]:
      for w in lst:
        pos = w.GetPosition()
        if pos.x != curx or pos.y != cury:
          w.MoveXY(curx, cury)
        (x,y) = w.GetBestSizeTuple()
        maxx=max(maxx,x)
        cury += y
    return(maxx,cury)

  def xxxfwdLayout(self):
    """Place the child windows appropriately within the parent window"""
    curx = 0
    cury = pSize[1]
    for lst in [self.permanentWindows,reversed(self.windows)]:
      for w in lst:
        if cury<0: # Its off the screen -- the top of the prior is off so this must also be off screen
          w.Hide()
        else:
          w.Show()
          (x,y) = w.GetBestSizeTuple()
          cury -= y
          w.MoveXY(curx, cury)


  def xxxlayout(self):
    """Place the child windows appropriately within the parent window"""
    pSize = self.parentWin.GetClientSizeTuple()
    curx = 0
    cury = pSize[1]
    for lst in [self.permanentWindows,reversed(self.windows)]:
      for w in lst:
        if cury<0: # Its off the screen -- the top of the prior is off so this must also be off screen
          w.Hide()
        else:
          w.Show()
          (x,y) = w.GetBestSizeTuple()
          cury -= y
          w.MoveXY(curx, cury)

  def resolve(self,tree):
    """Figure out the appropriate handler for this element, and call it"""
    tag = tree.tag
    lookupDict = self.tags
    # tag has a namespace.  Support a heirarchial dictionary by looking up the namespace first to see if it is in there with a subdictionary.  If its not I just look the tag up in the main dictionary
    if tree.tag[0] == "{": 
      namespace, tag = tree.tag[1:].split("}")
      lookupDict = lookupDict.get(namespace,lookupDict) # Replace the dictionary with the namespace-specific one, if such a dictionary is installed
    handler = lookupDict.get(tag, self.defaultHandler)
    handler(tree,self)

  

# Define File Drop Target class
class XmlShellDropTarget(wx.DropTarget):
   def __init__(self, parent):
      wx.DropTarget.__init__(self)
      self.win = parent

   def	OnDragOver(self, x, y, defd):
      print "drag over"

   def 	OnDrop(self, x, y):
      print "drop"
      return true
   def 	OnEnter(self, x, y, defd):
     print "enter"

   def 	OnLeave(self):
     print "leave"

class MyFileDropTarget(wx.FileDropTarget):
    """How can I handle both text and file drag/drop?"""
 
    #----------------------------------------------------------------------
    def __init__(self, window):
        """Constructor"""
        wx.FileDropTarget.__init__(self)
        self.window = window
 
    #----------------------------------------------------------------------
    def OnDropFiles(self, x, y, filenames):
        """
        When files are dropped, write where they were dropped and then
        the file paths themselves
        """
        pdb.set_trace()
        print str(filenames)



class XmlTerm(wx.Panel):
  """This is the main XML terminal panel.  Right now it behaves both as a terminal and a shell which is both awkward and powerful"""
  def __init__(self, parent,doc,resolver,completion,execute):
    #scrolled.ScrolledPanel.__init__(self, parent, style = wx.TAB_TRAVERSAL|wx.SUNKEN_BORDER)
    wx.Panel.__init__(self, parent, style = wx.TAB_TRAVERSAL|wx.SUNKEN_BORDER,size=(800,600))
    #wx.ScrolledWindow.__init__(self, parent, style = wx.TAB_TRAVERSAL|wx.SUNKEN_BORDER,size=(800,600))
    self.frame = parent
    self.windowMoverMode = False # Am I highlighting the child panels so they can be grabbed?
    self.resolver = resolver
    self.completion = completion
    self.executeCmd = execute
    self.size = self.GetClientSize()

    self.vscroll = wx.ScrollBar(self,style=wx.SB_VERTICAL)
    self.vstart = (0,0) # self.GetViewStart()
    self.vfrac = 1.0  # where am I in the document, fraction from 0 to 1 (scrollbar)
    self.vscroll.SetSize((20,self.size[1]))
    self.vscroll.SetPosition((self.size[0]-20,0))
    self.scrollBarGrabSize = 20

    self.resolver.parentWin = self
    self.doc = Document(resolver)
    self.doc.append(doc)
    self.doc.layout()
    self.selection = None  # did the user select a portion of the document?
    self.cmdLine = CmdLine(self,lambda x,s=self: s.execute(x), completion)
    self.resolver.permanentWindows = [self.cmdLine]
    self.aliases = {} # { 'ls':'ls -C'}
    try:
      f = open("frowny.svg","r")
      self.aliases[':-('] = "echo <widget><display>" + f.read() + "</display></widget>"
    except:
      pass  
    try:
      f = open("smiley.svg","r")
      self.aliases[':-)'] = "echo <widget><display>" + f.read() + "</display></widget>"
    except:
      pass  
      
    # self.frame.handOff(FancyText(self.frame,"This is a test"))

    self.Bind(wx.EVT_SIZE, self.OnSize) 
    self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouse) 
    self.vscroll.Bind(wx.EVT_SCROLL, self.OnScroll)
    self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)

    #self.dropTgt = XmlShellDropTarget(self)
    #self.frame.SetDropTarget(self.dropTgt)
    self.fileDrop = MyFileDropTarget(self)
    self.SetDropTarget(self.fileDrop)

    #self.virtualSize=(0,0)
    #self.SetScrollbars(1,1,1,1)  # ????
    #self.SetScrollRate(20,20)
    self.render()

  def OnMouseWheel(self,event):
    tic = float(event.GetWheelRotation())/float(event.GetWheelDelta())
    self.vfrac -= (tic * .02)  # 50 ticks to fully scroll
    if self.vfrac < 0: self.vfrac = 0.0
    if self.vfrac > 1: self.vfrac = 1.0
    # print "vfrac: ", self.vfrac
    self.render()
 
  def OnScroll(self,event):
    pos = event.GetPosition()
    et = event.GetEventType()
    if et in wx.EVT_SCROLL_THUMBRELEASE.evtType:  # the thumb release returns a bad position (its about 20 higher)  
      print "released at ", pos
    elif et in wx.EVT_SCROLL_ENDSCROLL.evtType: # the end scroll event returns a bad position (its about 20 higher)
      print "released at ", pos
    elif et in wx.EVT_SCROLLWIN_LINEUP.evtType:
      pass
    elif et in wx.EVT_SCROLLWIN_LINEDOWN.evtType:
      pass
    else:
      pos = event.GetPosition()
      # self.calcStartPos()
      self.vfrac = float(pos)/float(self.vscroll.GetSize()[1]-self.scrollBarGrabSize)
      print "On Scroll %f (%d) %d " % (self.vfrac, pos,event.GetEventType())
      self.render()

  def calcStartPos(self,frac):
    renderSz = self.size[1] - self.cmdLine.GetSize()[1]  # because its not part of the doc and is always on the bottom
    vScrollRange = max(0,self.vsize[1]-renderSz) # You can't scroll across the entire virtual size.  Scrolling ends when the BOTTOM of the screen is touching the BOTTOM of the virtual size
    topy = int(frac * float(vScrollRange))
    # topy = min(topy, self.vsize[1]-renderSz)  # Maximum scroll is where bottom of doc hits bottom of win 
    self.vstart = (self.vstart[0],topy )

  def calcDocSize(self):
    """Calculate size of the full document that the screen shows only a part of""" 
    docsize = self.doc.GetSize()
    size = self.GetClientSize()
    self.vsize = (max(docsize[0],size[0]),max(docsize[1],size[1]))


  def onCharEvent(self, event):  # If someone passes a key event to me give it to the command line
    self.cmdLine.keyPressed(event)

  def OnMouse(self,event):
    #pos = event.GetPositionTuple()  # can't use the position from the event because that is relative to window which may not be this window -- it may be an interior panel
    pos = self.ScreenToClient(wx.GetMousePosition())
    pos = (pos[0] + self.vstart[0], pos[1] + self.vstart[1])
    if event.MiddleDown():
      try:
        wx.TheClipboard.Open()
        wx.TheClipboard.UsePrimarySelection(True)
        data = wx.TextDataObject()
        ok = wx.TheClipboard.GetData(data)
        if not ok:
          wx.TheClipboard.UsePrimarySelection(False)
          ok = wx.TheClipboard.GetData(data)
        if ok:
          text = data.GetText()
          text = text.replace("\n",";") # I don't want returns in the command line
          self.cmdLine.append(text)
      finally:
        wx.TheClipboard.Close()       

      pass
    if event.LeftDown():
      print "start selection"
      #pdb.set_trace()
      print pos
      if self.selection:
        self.selection.complete()
        self.selection = None
      self.selection = self.doc.startSelection(pos)
      event.Skip()
    elif event.Dragging() and self.selection:
      self.doc.continueSelection(pos,self.selection)
      print "Dragging"
    elif event.LeftUp() and self.selection:
      print "selection complete"
      if not wx.TheClipboard.IsOpened():
        try:
          wx.TheClipboard.Open()
          wx.TheClipboard.UsePrimarySelection(True)
          data = wx.TextDataObject()
          data.SetText(self.selection.simpleString())
          wx.TheClipboard.SetData(data)
        finally:
          wx.TheClipboard.Close()       

  def relayout(self,panelLst):
    """Called when a list of child panels have changed size"""
    i = self.doc.rediscoverSizes(panelLst)
    self.doc.layout(i)
 
    self.render()
    
 
  def handOff(self,win,pos):
    """Called to give this window away to another parent"""
    self.doc.remove(win)
    self.frame.handOff(win,pos)
    self.render()

  def windowMover(self, val = None):
    """Shows the border of windows, was going to be used for moving"""
    if val is None:
      self.windowMoverMode = not self.windowMoverMode
    print "window mover %s" % (str(self.windowMoverMode))
    for doce in self.doc.doc:
      try:
        if doce.panel: doce.panel.setBorder(self.windowMoverMode)
      except AttributeError, e:
        pass # Not one of my windows 
        #doce.panel.Hide()
        #doce.panel.SetWindowStyle(newStyle)
        #doce.panel.Refresh()  # not working
        #doce.panel.Update()
        #doce.panel.Show()

    self.Refresh()
    self.Update()

  def execute(self,textLine):
    """Execute a command line.  More properly part of XML Shell functionality"""
    prompt = self.cmdLine.getPrompt()
    cmdprompt = '<text fore="#0000B0">%s%s</text>' % (escape(prompt), escape(textLine))
    # print cmdprompt
    self.doc.append(cmdprompt)
    self.executeCmd(textLine,self)
    
    self.doc.layout()
#    self.calcDocSize()
#    self.calcStartPos(1.0) # 0 is top 1 is bottom
    self.vfrac = 1.0 # after command is executed we drop to the bottom
    self.render()       

#  def downToBottom(self):   
#    self.calcDocSize() 
#    self.vstart = (0, max(0,self.vsize[1]-self.GetClientSize()[1]-self.cmdLine.GetSize()[1]))  # Go back to the bottom

  def OnSize(self,event):
      """Change the size of this window"""
      newsize = self.GetClientSize()
      if self.size != newsize:
        self.size = newsize
        self.vscroll.SetSize((20,self.size[1]))
        self.vscroll.SetPosition((self.size[0]-20,0))
        self.render()

        # print self.GetViewStart()
       
   
  def render(self):
    """Place the child panels appropriately in this panel"""
    cmdHeight = self.cmdLine.GetSize()[1]
    size = self.GetClientSize()
    self.calcDocSize()    
    #if self.vstart[1] >= docsize[1] - size[1]: # Is the view start near the bottom
    #  self.doc.positionFromBottom((self.size[0],self.size[1]-height))
    #else:
    self.calcStartPos(self.vfrac) # 0 is top 1 is bottom
    self.doc.position(self.vstart,size)

    size = (size[0], size[1] - cmdHeight)
    # self.vscroll.SetThumbPosition(int(float(size[1] * vstart[1])/self.vsize[1]))
    self.scrollBarGrabSize = float(size[1]) * float(self.size[1])/float(self.vsize[1])
    self.vscroll.SetScrollbar(int(float(size[1] * self.vstart[1])/self.vsize[1]),self.scrollBarGrabSize,size[1]+cmdHeight,True)
    self.vscroll.Show(True)

    self.Update()
    self.cmdLine.Raise()  # Cmd line draws on top of everything else
    cmdHeight = self.cmdLine.refresh()
    self.cmdLine.MoveXY(0,self.size[1]-cmdHeight)
    self.cmdLine.Update()

def completion(s):
  if not s:
    return ""
  cmds=["!time ", "!echo ", "export ","!export ", "alias ", "!alias ", "!name" ]
  for c in cmds:
    if c.startswith(s):
      print "complete", c
      return c[len(s):]
  return ""
      

def execution(textLine,xmlterm):
    """Execute the passed string"""
    cmdList = textLine.split(";")
    while cmdList:
      text = cmdList.pop(0) 
      sp = text.split()
      if sp:
        alias = xmlterm.aliases.get(sp[0],None)
        if alias: # Rewrite text with the alias and resplit
          sp[0] = alias
          text = " ".join(sp)
          sp = text.split()

        if sp[0]=="!time": # Show the time (for fun)
          xmlterm.doc.append("<time/>")
        elif sp[0] == '!echo':  # Display something on the terminal
          xmlterm.doc.append(" ".join(sp[1:]))
          if 0:
           try:  # If its good XML append it, otherwise excape it and dump as text
            rest = " ".join(sp[1:])
            testtree = ET.fromstring(rest)
            xmlterm.doc.append(rest)
           except ET.ParseError:
            xmlterm.doc.append(escape(rest))
        elif sp[0] == '!name':  # Change the terminal's title
          xmlterm.frame.SetTitle(sp[1])
        elif sp[0] == 'export' or sp[0] == '!export':   # Set an environment variable in the shell
          kv = " ".join(sp[1:]).split("=")
          key = kv[0].strip()
          val = kv[1].strip()
          os.environ[key]=val
        elif sp[0] == 'alias' or sp[0] == '!alias':  # Make one command become another
          xmlterm.aliases[sp[1]] = " ".join(sp[2:])
        else:
          xmlterm.doc.append('<process exec="%s"/>' % " ".join(sp))  

class MyMiniFrame(wx.MiniFrame):
    """When you pull a widget out of the main window, it is placed into this frame"""
    def __init__(self, parent, title, pos=wx.DefaultPosition, size=wx.DefaultSize,style=wx.DEFAULT_FRAME_STYLE):
        wx.MiniFrame.__init__(self, parent, -1, title, pos, size, style)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.Bind(wx.EVT_CHAR, self.onCharEvent)
        self.panels=[]    

    def onCharEvent(self, event):
        keycode = event.GetKeyCode()
        controlDown = event.CmdDown()
        altDown = event.AltDown()
        shiftDown = event.ShiftDown()
        print "miniframe %s got key" % self.GetTitle()
    

    def OnCloseWindow(self, event):
        self.Destroy()

    def handOff(self,panel,pos):
      return False

    def relayout(self,panelLst):
      """Called when a list of child panels have changed size"""
      #i = self.doc.rediscoverSizes(panelLst)
      #self.doc.layout(i)
      for p in panelLst: 
        p.render()
 

    def acceptPanel(self,panel,pos=(0,0)):
      panel.Reparent(self)
      panel.SetPosition(pos)
      if not self.panels:
        size = panel.GetSize()
        size.x = size.x + pos[0]
        size.y += pos[1]
        self.SetClientSize(size)
      self.panels.append(panel)

class MyFrame(wx.Frame):
    """ The primary frame"""
    def __init__(self, parent, title,panelFactory):
        wx.Frame.__init__(self, parent, -1, title, pos=(150, 150), size=(800, 600))
        self.panel = panelFactory(self)
        sizer = wx.BoxSizer()
        sizer.Add(self.panel, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.Bind(mainliner.EVT_EXECUTE,self.execute)

    def execute(self,evt):
      # pdb.set_trace()
      evt.thunk()

    def handOff(self,panel,pos):
      """Give a panel to another frame (right now this function can only create a new miniframe for the panel)"""
      name = " "
      try:
        name = str(panel.name)
      except:
        pass
      mf = MyMiniFrame(self,name) # ,pos=pos)
      mf.acceptPanel(panel)
      mf.FitInside()
      mf.Move(pos)
      mf.Show(True)
      return True


class App(wx.App):
    def __init__(self, panelFactory, redirect):
      self.panelFactory = panelFactory
      wx.App.__init__(self, redirect=redirect)
    def OnInit(self):
      self.frame = MyFrame(None, "XML Shell",self.panelFactory)
      self.SetTopWindow(self.frame)
      self.frame.Show(True)
      return True
        
app       = None

def GetDefaultResolver():
  resolver=XmlResolver()
  resolver.tags["time"] = timeHandler
  resolver.tags["img"] = imageHandler
  resolver.tags["text"] = textHandler
  resolver.tags["svg"] = svgHandler
  resolver.tags["plot"] = plotHandler
  resolver.tags["widget"] = widgetHandler
  resolver.tags["process"] = processHandler
  resolver.tags["list"] = listHandler
  return resolver

def Test():
  doc = ["<text size='100' fore='rgb(100,200,50)'>RICH TEXT TEST</text>",
  "<text size='50' fore='#FF40D0'>purple</text>",
  "<text size='25' fore='red'>red</text>",
  """<svg width='100' height='100'><circle cx='50' cy='50' r='40' stroke='green' stroke-width='4' fill='yellow' /></svg>""",
  """
  <widget name="plot">
  <display>
  <text>grab here</text>
  <plot title="TEST PLOT" xlabel="time" ylabel="memory">
    <series label="data 1">1,2,3,4,5,6,7,8</series>
    <series label="data 2">2,4,5,7,8,3,1,0</series>
  </plot>
  </display>
  </widget>
  """, 
  """
  <widget width="100" height="100" name="testWidget">
    <display>
      <svg width="100" height="100">
        <circle cx="50" cy="50" r="40" stroke="green" stroke-width="4" fill="red" />
      </svg>
      <fancy size='30' fore='rgb(100,200,50)'>This is a full widget</fancy>
    </display>
    <source>file:~/foo.txt</source>
    <refresh interval="10000">testWidget.refresh</refresh>
  </widget>""",
  """
  <list>
    <columns>
      <name/>
      <date/>
    </columns>
    <data>
      <row><name>Joe Smith</name><date>Oct 1,2011</date></row>
      <row><name>John Doe</name><date>Oct 2,2011</date></row>
      <row><name>Jim</name><date>Oct 3,2011</date></row>

    </data>
  </list>
  """
]
  main(doc)


def main(doc=None):
  global app
  os.environ["TERM"] = "XT1" # Set the term in the environment so child programs know xmlterm is running
  resolver=XmlResolver()
  resolver.tags["time"] = timeHandler
  resolver.tags["img"] = imageHandler
  resolver.tags["text"] = textHandler
  resolver.tags["svg"] = svgHandler
  resolver.tags["plot"] = plotHandler
  resolver.tags["widget"] = widgetHandler
  resolver.tags["process"] = processHandler
  resolver.tags["list"] = listHandler
  # resolver.tags["process"] = processHandler

  if not doc:
    doc=[]
  app = App(lambda parent,doc=doc,resolver=resolver,completion=completion,execute=execution: XmlTerm(parent,doc,resolver,completion,execute),redirect=False)
  app.MainLoop()



if __name__ == "__main__":
    main()

# !echo <bdata length="10"><>><567890</bdata>
# !echo <widget name="test"><display><svg width="100" height="100"><circle cx="30" cy="30" r="20" stroke="green" stroke-width="4" fill="red" /></svg></display></widget>
# !echo <text size="80">TESTING</text>
# !echo <widget name="test"><display><svg width="100" height="100"><circle cx="50" cy="50" r="40" stroke="blue" stroke-width="4" fill="yellow" /></svg></display></widget>

# <svg width=\'100\' height=\'100\'><circle cx=\'50\' cy=\'50\' r=\'40\' stroke=\'green\' stroke-width=\'4\' fill=\'yellow\' /></svg>
