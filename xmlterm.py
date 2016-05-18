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
import traceback,sys,code, inspect
import sys, time, types
import math
import os
import re
import string
import pdb
import urlparse
import urllib
import svg
import json
import ConfigParser as configparser
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

DEFAULT_WINDOW_SIZE = (600,900)

DropToDebugger = True

HelpNameColor = (50,50,0xff)
HelpNameSize  = 24
HelpBriefColor = (50,50,0xa0)
HelpBriefSize  = 20

BorderStyle=wx.SIMPLE_BORDER #wx.NO_BORDER
ErrorColor="#FF4040"

from xmlpanels import *
from xmlcmdline import *
from xmldoc import *

class CommandException(Exception):
  pass

class CommandBadArgException(Exception):
  pass

class ParsingContext:
  """This object is passed around as XML entity tree is parsed.  You can use it to communicate state from outer or higher XML nodes to subsequent ones
     The xpath of the current element is stored in .path as a list of parent tag names.
  """
  def __init__(self,path=None):
    if not path: self.path = []
    else: self.path = path

def indent(elem,depth=0):
  if type(elem) in types.StringTypes:
    try:
      elem = ET.fromstring(elem)
    except ET.ParseError, e: # Its bad XML so just do something simple that breaks up lines
      return elem.replace(">",">\n")
  ret = ["  "*depth + "<" + elem.tag]
  for a in elem.attrib.items():
    ret.append(" " + a[0] + "=" + '"' + a[1] + '"')
  ret.append(">")
  if elem.text: ret.append(elem.text)
  if len(elem):
    ret.append("\n")
    for c in elem:
      ret.append(indent(c,depth+1))
  if elem.tail: ret.append(elem.tail)
  ret.append("</" + elem.tag + ">")
  ret.append("\n")
  return "".join(ret)

def barGraphHandler(elem,resolver,context):
  w=BarPanel(resolver.parentWin,elem)
  resolver.add(w)

def timeHandler(elem,resolver,context):
  """Create a representation of the 'time' XML tag"""
  w=TimePanel(resolver.parentWin)
  resolver.add(w)

def listHandler(elem,resolver,context):
  """Create a representation of the 'list' XML tag"""
  w=ListPanel(resolver.parentWin,elem)
  resolver.add(w)

ext2type = { ".bmp": wx.BITMAP_TYPE_BMP, ".gif": wx.BITMAP_TYPE_GIF, ".png":wx.BITMAP_TYPE_PNG, ".jpg":wx.BITMAP_TYPE_JPEG,".jpeg":wx.BITMAP_TYPE_JPEG}

def imageHandler(elem,resolver,context):
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

def helpCmdHandler(elem,resolver,context):
  """Create a graphical representation of the XML 'text' tag"""
  # pdb.set_trace()

  style = elem.attrib.get("style","full")

  name = elem.find("helpCmdName")
  if name is not None:
    name=name.text
  resolver.add(FancyText(resolver.parentWin,name,fore=HelpNameColor,size=HelpNameSize))

  if style=="brief":
    brief = elem.find("helpBrief")
    if brief is not None:
      brief = brief.text
    if brief: resolver.add(FancyText(resolver.parentWin,brief,fore=HelpBriefColor,size=HelpBriefSize))

  if style=="full":
    details = elem.find("helpDetails")
    if details is not None:
      resolver.resolve(details,context)


def textHandler(elem,resolver,context):
  """Create a graphical representation of the XML 'text' tag"""
  if elem.text:
    size = elem.attrib.get("size",None)
    if size: size = int(size)
    fore = elem.attrib.get("fore",None)
    if fore: fore = color.rgb(fore) # [ int(x) for x in fore.split(",")]
    back = elem.attrib.get("back",None)
    if back: back = color.rgb(back) # [ int(x) for x in back.split(",")]
    w = FancyTextChunked(resolver.parentWin,elem.text,fore=fore, back=back,size=size,chunkSize=2048)
    resolver.add(w)

def svgHandler(elem, resolver,context):
  """Create a graphical representation of the XML 'svg' tag"""
  # pdb.set_trace()
  w = SvgPanel(resolver.parentWin, elem)
  resolver.add(w) 

def plotHandler(elem, resolver,context):
  """Create a graphical representation of the XML 'plot' tag"""
  w = PlotPanel(resolver.parentWin, elem)
  resolver.add(w) 

def widgetHandler(elem, resolver,context):
  """Create a graphical representation of the XML 'widget' tag.  A widget is a wrapper around a group of other entities that can be manipulated as a unit by the terminal"""
  r = resolver.new()
  r.tags=resolver.tags # reference the main resolver dictionary in this subresolver
  w = WidgetPanel(resolver.parentWin, elem,r)
  resolver.add(w) 

def processHandler(elem, resolver,context):
  """create a GUI for the 'process' tag.  This will actually execute the specified process and pipe input/output between this program and the process"""  
  r = resolver.new()
  r.tags=resolver.tags # reference the main resolver dictionary in this subresolver
  w = ProcessPanel(resolver.parentWin, elem,r)
  resolver.add(w) 


def defaultHandler(elem,resolver,context):
  """Handle normal text and any XML that does not have a handler"""
  if elem.text and elem.text.strip():
    #w = wx.StaticText(resolver.parentWin,-1,elem.text)
    w = FancyText(resolver.parentWin,elem.text)
    resolver.add(w) # ,0,wx.ALL | wx.EXPAND,0)

  context.path.append(elem.tag)
  for child in elem:
    resolver.resolve(child,context)
    if child.tail and child.tail.strip():
      # w = wx.StaticText(resolver.parentWin,-1,child.tail,style = wx.BORDER_NONE)
      w = FancyText(resolver.parentWin,child.tail)
      resolver.add(w) # ,0,wx.ALL | wx.EXPAND,0)
  del context.path[-1]   

def getFunctionHelp(fn):
  #if fn.__name__ == "do_connect":
  #  pdb.set_trace()

  # TODO gather info from the arguments
  #argspec = inspect.getargspec(fn)

  if fn.__doc__:
    brief = ""
    doc = ""
    tmp = fn.__doc__
    if tmp[0] == "?":  # YaDoG style documentation
      tmp=tmp[1:]
    if 1:
      bpos = tmp.find("\n")  # Finds the first of \n or .
      bpos = tmp.find(".",0,bpos) 
      doc = "<helpDetails>" + tmp + "</helpDetails>"
      if bpos != -1:
        brief = "<helpBrief>" + tmp[0:bpos] + "</helpBrief>"
      elif len(tmp)<120: 
        brief = "<helpBrief>" + tmp + "</helpBrief>"
      else:
        pass
 
    return [brief,doc]  # TODO interprete and xmlize the docstring
  else:
    return ["<helpBrief>No help available</helpBrief>"]

def getDictCommandHelp(d, prefix="",single=None):
  ret = []
  for (name,val) in d.items():
    if name is None: name = "" # convert to something printable
    hlp = []
    if type(val) is types.DictType:
      tmp = prefix + name + " "
      hlp = getDictCommandHelp(val, tmp,single=single)
    else:
      if val[0] and (type(val[0]) == types.FunctionType or type(val[0]) == types.MethodType or type(val[0]) == types.LambdaType ):
        if not single or single == prefix + name:
          hlp = ["<helpCmd><helpCmdName>" + prefix + name + "</helpCmdName>"] + getFunctionHelp(val[0]) + ["</helpCmd>"]
    ret += hlp
  print ret
  return ret  


class XmlResolver:
  """This class turns an XML ElementTree representation into GUI widgets"""
  def __init__(self):
    self.tags = {}
    self.cmds = [] # list of classes used to resolve implicit commands
    self.sizer = None
    self.parentWin = None
    self.windows=[]
    self.permanentWindows=[]
    self.defaultHandler = defaultHandler
    self.xmlterm = None
    self.helpdoc = None

  def addCmds(self,cmds):
    if cmds:
      cmds.setContext(self)
      self.cmds.append(cmds)
    
  def getHelp(self,command=None):
    ret = []
    if command:  # Filter specific commands
      for c in command:
        for cmdContext in self.cmds:
          if hasattr(cmdContext,"commands"):  # If the object has a command lookup table, then print help on it
            ret += getDictCommandHelp(cmdContext.commands,single=c)
          fnname = "do_" + c
          if hasattr(cmdContext,fnname):
            ret += [ "<helpCmd><helpCmdName>" + fnname[3:] + "</helpCmdName>"] + getFunctionHelp(getattr(cmdContext,fnname)) + ["</helpCmd>"]        
    else: # Get all commands
      if self.helpdoc:
        ret.append(self.helpdoc)

      for cmdContext in self.cmds:
        if hasattr(cmdContext,"helpdoc") and cmdContext.helpdoc:   # Put the command category's help doc up
          ret.append(cmdContext.helpdoc)
        if hasattr(cmdContext,"commands"):  # If the object has a command lookup table, then print help on it
          ret += getDictCommandHelp(cmdContext.commands)
        for fnname in dir(cmdContext):    # IF the object has do_ functions print help on them.
          if fnname.startswith("do_"):
            ret += [ "<helpCmd><helpCmdName>" + fnname[3:] + "</helpCmdName>"] + getFunctionHelp(getattr(cmdContext,fnname)) + ["</helpCmd>"]
    return "\n".join(ret)

  def bindCmd(self,cmds,lst):
    """This function takes a nested dictionary which maps command to implementation function, and a list of user input tokens.  It attempts to bind the user input to a command in the dictionary and returns:
    ((function, completion_function), [args],{kwargs}) if it succeeds or
    (None, None, None) if there is no binding
    """
    idx = 0
    out = cmds.get(lst[0],None)
    if out is not None:
      if type(out) is types.DictType:  # Recurse into the next level of keyword
        ret = self.bindCmd(out,lst[1:])
        return ret
      else:
        return (out,lst[1:],None)  # TODO keyword args

    default = cmds.get(None,None)  # If there's a dictionary entry whose key is None, then this is used if nothing else matches
    if default:
      return (default,lst, None) # TODO keyword args
    return (None, None,None)

  def newContext(self):
    t = os.environ.get("PWD","")
    path = t.split("/")
    return ParsingContext(path)

  def start(self,xt):
    self.xmlterm = xt

  def clear(self):
    for w in self.windows:
      w.Destroy()
    self.windows = []

  def add(self,window):
    if not type(window) is types.ListType:
      window = [window]
      
    for w in window:
      w.Fit()
      self.windows.append(w)

  def getWindow(x,y):
    for w in self.windows:
      winRect = w.GetRect()

  def new(self):
    """Factory: return another instance of this object"""
    return XmlResolver()


  def resolve(self,tree,context):
    """Figure out the appropriate handler for this element, and call it"""
    tag = tree.tag
    lookupDict = self.tags
    # tag has a namespace.  Support a heirarchial dictionary by looking up the namespace first to see if it is in there with a subdictionary.  If its not I just look the tag up in the main dictionary
    if tree.tag[0] == "{": 
      namespace, tag = tree.tag[1:].split("}")
      lookupDict = lookupDict.get(namespace,lookupDict) # Replace the dictionary with the namespace-specific one, if such a dictionary is installed
    handler = lookupDict.get(tag, self.defaultHandler)
    handler(tree,self,context)

  def prompt(self):
    return os.environ.get("PWD","") + ">"

  def completion(self,s):
    if not s:
      return ""
    cmds=["!time ", "!exit", "exit", "!echo ", "export ","!export ", "alias ", "!alias ", "!name","!cd","cd" ]
    for c in cmds:
      if c.startswith(s):
        # print "complete", c
        return c[len(s):]
    return ""

  def error(s):
    return '<text fore="%s">%s</text>' % (ErrorColor,s)

  def execute(self,textLine,xmlterm):
    """Execute the passed string"""
#   try:
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
        self.executeOne(sp,xmlterm)

  def executeOne(self,sp,xmlterm):
        for cmdClass in self.cmds:
          if hasattr(cmdClass,"commands"):
            (fns,args,kwargs) = self.bindCmd(cmdClass.commands,sp)
            if fns: 
              (binding,completion) = fns
              if binding:
                if kwargs:
                  output = binding(*args,**kwargs)
                else:
                  output = binding(*args)
                if output is not None: # None means to continue looking for another command
                  if output:  # Commands will return "" if they have no output
                    xmlterm.doc.append(output)
                  return
          fn_name = "do_" + sp[0]
          if hasattr(cmdClass,fn_name):
            try:
              print "executing:", str(cmdClass.__class__), fn_name
              output = getattr(cmdClass,fn_name)(*sp[1:])
              if output is not None:  # None means keep looking -- I did not execute a command
                if output:   # "" means command worked but nothing output
                  xmlterm.doc.append(output)
                return
            except TypeError, e:  # command had incorrect arguments or something
              if DropToDebugger:
                type, value, tb = sys.exc_info()
                traceback.print_exc()
                last_frame = lambda tb=tb: last_frame(tb.tb_next) if tb.tb_next else tb
                frame = last_frame().tb_frame
                pdb.post_mortem()
              # TODO: print the command's help and try to hint at the problem
              xmlterm.doc.append("<error>" + str(e) + "</error>")
              return
        if sp[0]=="cd" or sp[0]=="!cd":
          cwd = os.environ.get("PWD")
          cwd = os.path.abspath(os.path.join(sp[1]))
          if os.path.isdir(cwd):
            os.environ["PWD"]=cwd
            xmlterm.cmdLine.setPrompt()  # Update the prompt
            os.chdir(cwd)
          else:
            xmlterm.doc.append(self.error('No such directory [%s]' % cwd))
        elif sp[0]=="!time": # Show the time (for fun)
          xmlterm.doc.append("<time/>")
        elif sp[0] == '!exit' or sp[0] == 'exit':  # goodbye
          self.xmlterm.frame.Close()
        elif sp[0] == '!echo':  # Display something on the terminal
          xmlterm.doc.append(" ".join(sp[1:]))
          if 0:
           try:  # If its good XML append it, otherwise escape it and dump as text
            rest = " ".join(sp[1:])
            testtree = ET.fromstring(rest)
            xmlterm.doc.append(rest)
           except ET.ParseError:
            xmlterm.doc.append(escape(rest))
        elif sp[0] == '!name':  # Change the terminal's title
          xmlterm.frame.SetTitle(sp[1])
        elif sp[0] == 'export' or sp[0] == '!export':   # Set an environment variable in the shell
          kv = " ".join(sp[1:]).split("=")
          if len(kv) == 2:
            key = kv[0].strip()
            val = kv[1].strip()
            os.environ[key]=val
          else:
            xmlterm.doc.append("usage: !export NAME=VALUE")
        elif sp[0] == 'alias' or sp[0] == '!alias':  # Make one command become another
          xmlterm.aliases[sp[1]] = " ".join(sp[2:])
        else:
          t = escape(" ".join(sp))
          print t
          xmlterm.doc.append('<process>%s</process>' % t)  

  

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

class LookAndFeel:
  def __init__(self):
    self.backCol = wx.Color(80,80,80,100)
  
class XmlTerm(wx.Panel):
  """This is the main XML terminal panel.  Right now it behaves both as a terminal and a shell which is both awkward and powerful"""
  def __init__(self, parent,doc,termController, config, LaF=None):
    self.config = config
    wx.Panel.__init__(self, parent, style = wx.TAB_TRAVERSAL|wx.SUNKEN_BORDER)
    self.ScrollBarWidth = 0 # reported by the scrollbar
    self.MouseWheelTicsPerScreen = 10.0 # How many mouse wheel motions to scroll by a full screen?
    if LaF: self.LaF = LaF  #? Look and Feel 
    else:
      self.LaF = LookAndFeel()
    self.frame = parent #? pointer to the primary GUI frame
    self.windowMoverMode = False #? Am I highlighting the child panels so they can be grabbed?
    self.resolver = termController  #?  The resolver converts xml to panels
    self.completion = termController #? Command line completion
    self.executeCmd = termController #? Execute a command entered in the prompt
    
    self.SetBackgroundColour(self.LaF.backCol)

    tmp = parent.GetClientSize()
    #self.SetClientSize(tmp)  #? Window's display size (minus scrollbar and prompt)
    self.size = tmp
    
    self.cmdLine = CmdLine(self,lambda x,s=self: s.execute(x), self.completion)  #? Text entry window
    self.cmdLine.SetBackgroundColour(self.LaF.backCol)
    #cmdLinePos = self.cmdLine.GetPosition()

    #tmp = (tmp[0] - self.ScrollBarWidth, cmdLinePos[1] - 2) # tmp[1] - cmdLineSize[1]*5)    
    #self.docPanel.SetSize((tmp[0]-50-self.ScrollBarWidth,tmp[1]-10))
    #self.docPanel.SetPosition((0,0))

    self.vscroll = wx.ScrollBar(self,style=wx.SB_VERTICAL)
    size = self.vscroll.GetSize()
    self.ScrollBarWidth = size[0]

    assert(self.vscroll.SetBackgroundColour(self.LaF.backCol))
    assert(self.vscroll.SetForegroundColour(wx.Colour(255,0,0,255)))
    #self.vscroll.SetBrush(wx.Brush(wx.Colour(255,0,0),wx.SOLID))
    #self.vscroll.SetBackground(wx.Brush(wx.Colour(255,0,0),wx.SOLID))
    #self.vscroll.
    
    self.vstart = (0,0) # self.GetViewStart()
    self.vsize = (0,0)  # Full document size
    self.vfrac = 1.0  # where am I in the document, fraction from 0 to 1 (scrollbar)
    self.vscroll.SetSize((self.ScrollBarWidth,self.size[1]))
    self.vscroll.SetPosition((self.size[0]-self.ScrollBarWidth,0))
    self.scrollBarGrabSize = self.size[1]

    self.docPanel = wx.Panel(self, pos=(0,0),style = wx.NO_BORDER)
    self.docPanel.SetBackgroundColour(self.LaF.backCol)

    # debugging: self.docPanel.SetBackgroundColour(wx.Color(255,0,0,255))

    self.resolver.parentWin = self.docPanel
    self.doc = Document(self.resolver)
    self.doc.append(doc)
    self.doc.layout()
    self.selection = None  # did the user select a portion of the document?
    # self.resolver.permanentWindows = [self.cmdLine]
    self.aliases = {} # { 'ls':'ls -C'}
      
    # self.frame.handOff(FancyText(self.frame,"This is a test"))

    self.Bind(wx.EVT_MOVE, self.OnReposition) 
    self.Bind(wx.EVT_SIZE, self.OnSize) 
    self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouse) 
    self.vscroll.Bind(wx.EVT_SCROLL, self.OnScroll)
    self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)

    # Bind to handle up/down arrow and enter
    self.Bind(wx.EVT_CHAR, self.cmdLine.keyReceiver)
    self.docPanel.Bind(wx.EVT_CHAR, self.cmdLine.keyReceiver)

#    self.docPanel.Bind(wx.EVT_SET_FOCUS,self.OnFocus)
#    self.Bind(wx.EVT_KILL_FOCUS,self.OnFocus)


    #self.dropTgt = XmlShellDropTarget(self)
    #self.frame.SetDropTarget(self.dropTgt)
    self.fileDrop = MyFileDropTarget(self)
    self.SetDropTarget(self.fileDrop)

    #self.virtualSize=(0,0)
    #self.SetScrollbars(1,1,1,1)  # ????
    #self.SetScrollRate(20,20)
    self.resolver.start(self)
    self.render()

# Does not seem to transition focus
#  def OnFocus(self,event):
#    wx.PostEvent(self.cmdLine.entry,event)        

  def OnMouseWheel(self,event):
    tic = float(event.GetWheelRotation())/float(event.GetWheelDelta())
    # How far should the wheel scroll per tic?
    # Discover how many screens in the full document:
    sindoc = float(self.vsize[1])/self.size[1]
    fracPerTic = 1.0/(sindoc*self.MouseWheelTicsPerScreen)
  
    self.vfrac -= (tic * fracPerTic)  # 50 ticks to fully scroll
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
    """Calculates the position in the document that corresponds to the top left of the screen"""
    renderSz = self.docPanel.GetClientSize()
    vScrollRange = max(0,self.vsize[1]-renderSz[1]) # You can't scroll across the entire virtual size.  Scrolling ends when the BOTTOM of the screen is touching the BOTTOM of the virtual size
    topy = int(frac * float(vScrollRange))
    # topy = min(topy, self.vsize[1]-renderSz)  # Maximum scroll is where bottom of doc hits bottom of win 
    self.vstart = (self.vstart[0],topy )

  def calcDocSize(self):
    """? Calculate size of the full document that the screen may only show a part of.  
       This is is the maximum of the window size and the document size
    """ 
    docsize = self.doc.GetSize()
    size = self.docPanel.GetClientSize()
    self.vsize = (max(docsize[0],size[0]),max(docsize[1],size[1]))


  def onCharEvent(self, event):  # If someone passes a key event to me give it to the command line
    if key=="c" or key == "C" and evt.ControlDown():  # COPY
      if not wx.TheClipboard.IsOpened():
        try:
          wx.TheClipboard.Open()
          data = wx.TextDataObject()
          data.SetText(self.selection.simpleString())
          wx.TheClipboard.SetData(data)
        finally:
          wx.TheClipboard.Close()       
    else:
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
    print self.cmdLine.GetSize()
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
   try:
    prompt = self.cmdLine.getPrompt()
    cmdprompt = '<text fore="#0000B0">%s%s</text>' % (escape(prompt), escape(textLine))
    # print cmdprompt
    self.doc.append(cmdprompt)
    self.executeCmd.execute(textLine,self)
    
    self.doc.layout()
#    self.calcDocSize()
#    self.calcStartPos(1.0) # 0 is top 1 is bottom
    self.vfrac = 1.0 # after command is executed we drop to the bottom
    self.render()       
   except:
        type, value, tb = sys.exc_info()
        traceback.print_exc()
        last_frame = lambda tb=tb: last_frame(tb.tb_next) if tb.tb_next else tb
        frame = last_frame().tb_frame
        pdb.post_mortem()
        raise
        #ns = dict(frame.f_globals)
        #ns.update(frame.f_locals)
        #code.interact(local=ns)
#  def downToBottom(self):   
#    self.calcDocSize() 
#    self.vstart = (0, max(0,self.vsize[1]-self.GetClientSize()[1]-self.cmdLine.GetSize()[1]))  # Go back to the bottom

  def OnReposition(self,event):
      """Change the position of this window"""
      pos = event.GetPosition()
      self.config.set("LookAndFeel","position",json.dumps(pos.Get()))

  def OnSize(self,event):
      """Change the size of this window"""
      newsize = self.GetClientSize()
      if self.size != newsize:
        self.size = newsize
        self.vscroll.SetSize((self.ScrollBarWidth,self.size[1]))
        self.vscroll.SetPosition((self.size[0]-self.ScrollBarWidth,0))
        self.render()
        self.config.set("LookAndFeel","size",json.dumps(self.size.Get()))
       
   
  def render(self):
    """Place the child panels appropriately in this panel"""
    # print "render"
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
    # does not work: self.cmdLine.Raise()  # Cmd line draws on top of everything else
    cmdHeight = self.cmdLine.refresh()
    self.cmdLine.MoveXY(0,self.size[1]-cmdHeight)
    self.cmdLine.Update()

    self.docPanel.SetSize((size[0]-self.ScrollBarWidth-1,self.size[1]-cmdHeight))


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
    def __init__(self, parent, title, panelFactory,size=DEFAULT_WINDOW_SIZE,position=None):
        wx.Frame.__init__(self, parent, -1, title, pos=position, size=size)
        self.panel = panelFactory(self)
        sizer = wx.BoxSizer()
        sizer.Add(self.panel, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.Bind(mainliner.EVT_EXECUTE,self.execute)
        self.Bind(wx.EVT_MOVE, self.OnReposition) 
        self.SetTransparent(128) 

    def OnReposition(self,event):
      """Change the position of this window"""
      self.panel.OnReposition(event)  # I call into the child so it can write the config file.  This saves passing the config to the frame

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
    def __init__(self, panelFactory, redirect,size=None,position=None):
      self.panelFactory = panelFactory
      self.size = size
      self.position = position
      wx.App.__init__(self, redirect=redirect)
    def OnInit(self):
      self.frame = MyFrame(None, "XML Shell",self.panelFactory,size=self.size,position=self.position)
      self.SetTopWindow(self.frame)
      self.frame.Show(True)
      return True
        
app       = None

def GetDefaultResolverMapping():
  resolver={}
  resolver["time"] = timeHandler
  resolver["img"] = imageHandler
  resolver["text"] = textHandler
  resolver["svg"] = svgHandler
  resolver["plot"] = plotHandler
  resolver["barGraph"] = barGraphHandler
  resolver["widget"] = widgetHandler
  resolver["process"] = processHandler
  resolver["list"] = listHandler
  resolver["helpCmd"] = helpCmdHandler
  resolver["helpDetails"] = defaultHandler
  return resolver

def Test():
  # pdb.set_trace()
  foo = """<a>test<b>b</b><c k1="z" k2="y">cval</c></a>"""
  print indent(foo)

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
  """,
  """<barGraph title="test" xlabel="bottom label" ylabel="vertical label">
     <a>30</a>
     <b label='labelB'>20</b>
     <c label='C'>10</c>
     <d label='D'>5</d>
     <a1>30</a1>
     <b1>20</b1>
     <c1>10</c1>
     <d1>5</d1>
     <a2>30</a2>
     <b2>20</b2>
     <c2>10</c2>
     <d2>5</d2>
     </barGraph>
  """
]
  main(doc)


def main(doc=None):
  global app
  os.environ["TERM"] = "XT1" # Set the term in the environment so child programs know xmlterm is running
  resolver=XmlResolver()
  resolver.tags= GetDefaultResolverMapping()

  aliases = {}
  try:
      f = open("frowny.svg","r")
      aliases[':-('] = "echo <widget><display>" + f.read() + "</display></widget>"
  except:
      pass  
  try:
      f = open("smiley.svg","r")
      aliases[':-)'] = "echo <widget><display>" + f.read() + "</display></widget>"
  except:
      pass  

  if not doc:
    doc=[]

  config = ConfigParser.SafeConfigParser()
  config.read(".xmlterm.cfg")  

  app = App(lambda parent,doc=doc,resolver=resolver: XmlTerm(parent,doc,resolver,config),redirect=False)
  app.MainLoop()



if __name__ == "__main__":
    main()

# !echo <bdata length="10"><>><567890</bdata>
# !echo <widget name="test"><display><svg width="100" height="100"><circle cx="30" cy="30" r="20" stroke="green" stroke-width="4" fill="red" /></svg></display></widget>
# !echo <text size="80">TESTING</text>
# !echo <widget name="test"><display><svg width="100" height="100"><circle cx="50" cy="50" r="40" stroke="blue" stroke-width="4" fill="yellow" /></svg></display></widget>

# <svg width=\'100\' height=\'100\'><circle cx=\'50\' cy=\'50\' r=\'40\' stroke=\'green\' stroke-width=\'4\' fill=\'yellow\' /></svg>
