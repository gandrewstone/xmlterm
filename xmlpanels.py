from ast import literal_eval
import sys, time, types, traceback
import math
import os
import re
import string
import glob
import pdb
import urlparse
import urllib
import svg
import select, subprocess, fcntl
from string import Template

from xml.sax.saxutils import escape,unescape

import xml.etree.ElementTree as ET

import wx.lib.scrolledpanel as scrolled
import wx.gizmos as gizmos
import wx.lib.plot as plot
import wx.richtext
#import wx.lib.fancytext
import wx
import wx.aui

AliveColor = (220,255,180)  #? This process is still alive
CursorChar = chr(219)


import matplotlib
matplotlib.use('WXAgg')

from numpy import arange,sin,pi
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure as Figure

from xmldoc import *
import color

def intersperse(lst, item):
    result = [item] * (len(lst) * 2 - 1)
    result[0::2] = lst
    return result

def GetExternalEntity(entityText):
  print "Get external entity: ", entityText

DefaultStyle = wx.NO_BORDER
# DefaultStyle = wx.SIMPLE_BORDER

DefaultBorderColor = (0,50,250)

SelectedColor = wx.Colour(240,240,150)

class XmlPanel(wx.Panel):
  """The base class for all panels that represent some XML document"""
  def __init__(self,parent,style=None):
    if style is None:
      style=DefaultStyle
    wx.Panel.__init__(self, parent, -1,style=style)
    self.parent = parent
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.border = False
    self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouse) #here I am binding the event.
    self.Bind(wx.EVT_CHAR, self.onCharEvent) 
    self.grabbable = False
    self.brush = None  #? The current background brush
    self.defaultBrush = None  #? The default one (when not selected)
    self.selected = False
    self.createdAt = traceback.extract_stack()[-3]

  def move(self,x,y):
    pos = self.GetPosition()
    if pos[0] != x or pos[1] != y:
      self.MoveXY(x,y)


  def simpleString(self):
    """Returns the context of this panel as a string with no markup"""
    return None

  def setSelected(self,state):
    if self.selected != state:
      if state:
        self.defaultBrush = self.brush
        self.brush = wx.Brush(SelectedColor,wx.SOLID)
        self.SetBackgroundColour(SelectedColor)
      else:
        self.brush = self.defaultBrush
        if self.brush: self.SetBackgroundColour(self.brush.GetColour())
        else: self.SetBackgroundColour(self.parent.GetBackgroundColour())
      self.selected = state
      self.Refresh()
      self.Update()

  def handOff(self,win,scrnPos):
    """Giving this child away -- by default let the parent deal with it"""
    self.parent.handOff(win,scrnPos)

  def onCharEvent(self, event):  # If someone passes a key event to me, pass to parent by default, but you can override
    #self.parent.onCharEvent(event)
    event.ResumePropagation(100)  # TODO: Do I need to discover my depth and limit propagation?
    event.Skip()

  def OnMouse(self,event):
    """Mouse control"""

    if event.LeftDown() and event.ControlDown(): # If you ctrl-left click, this will extract the panel from the parent (if the panel allows it)
      #print "left down"
      #self.SetFocusIgnoringChildren()
      #self.SetFocus()
      if not self.grabbable:  # If the panel does not allow extraction, hand the click event to someone else.
        event.ResumePropagation(100)
        event.Skip()
      else:
        pos = event.GetPosition()
        poss = self.ClientToScreen(pos)  # Where am I clicking so the new frame can be place there?

        self.parent.handOff(self,poss)  # Ok give away the window
        self.parent = self.GetParent()  # and update who I gave it to
        return
    else:  # We didn't care about this mouse event, so give it to someone else
      event.ResumePropagation(100) 
      event.Skip()

  def setBorder(self,val):
    """XML panels can have a custom-drawn border.  WX borders do not work reliably, I think they are overwritten when the window is cleared""" 
    self.border = val
    self.Refresh()
    self.Update()  

  def OnPaint(self,evt):
    dc = wx.PaintDC(self)
    self.paintXmlPanel(dc)

  def paintXmlPanel(self,dc):
    """Repaint this panel.  Right now, this code just draws the border if it is on"""
    #try:
    #  print "panel [%s] text [%s]" % (str(self),str(self.createdAt))
    #except:
    #  pass
    if self.brush is None:
      # bkcol = self.parent.GetBackgroundColour()
      brush = wx.Brush(wx.Colour(0,0,0),wx.TRANSPARENT)
    else: brush = self.brush
    sz = self.GetSize()
    oldb = dc.GetBrush()
    oldp = dc.GetPen()
      # brush = wx.Brush(wx.Colour(0,0,0),wx.TRANSPARENT)
    if self.border:
      pen = wx.Pen(wx.Colour(*DefaultBorderColor), 1,wx.SOLID)
    else:
      pen = wx.Pen(wx.Colour(0,0,0), 1,wx.TRANSPARENT)
    dc.SetPen(pen)
    dc.SetBrush(brush)
    dc.DrawRectangle(0,0,sz[0]-1, sz[1]-1)  # TODO: make a prettier border
    dc.SetBrush(oldb)
    dc.SetPen(oldp)    

someColors = ['MEDIUM FOREST GREEN', 'RED', 'GOLDENROD', 'SALMON', 'BLUE', 'GOLD', 'MEDIUM ORCHID', 'SEA GREEN', 'BLUE VIOLET', 'MEDIUM SEA GREEN', 'SIENNA', 'BROWN', 'GREY', 'MEDIUM SLATE BLUE', 'SKY BLUE', 'CADET BLUE', 'GREEN', 'MEDIUM SPRING GREEN', 'SLATE BLUE', 'CORAL', 'GREEN YELLOW', 'MEDIUM TURQUOISE', 'SPRING GREEN', 'CORNFLOWER BLUE', 'INDIAN RED', 'MEDIUM VIOLET RED', 'STEEL BLUE', 'CYAN', 'KHAKI', 'MIDNIGHT BLUE', 'TAN', 'DARK GREY', 'LIGHT BLUE', 'NAVY', 'THISTLE', 'DARK GREEN', 'LIGHT GREY', 'ORANGE', 'TURQUOISE', 'DARK OLIVE GREEN', 'LIGHT STEEL BLUE', 'ORANGE RED', 'VIOLET', 'DARK ORCHID', 'LIME GREEN', 'ORCHID', 'VIOLET RED', 'DARK SLATE BLUE', 'MAGENTA', 'PALE GREEN', 'WHEAT', 'DARK SLATE GREY', 'MAROON', 'PINK', 'WHITE', 'DARK TURQUOISE', 'MEDIUM AQUAMARINE', 'PLUM', 'YELLOW', 'DIM GREY', 'MEDIUM BLUE', 'PURPLE', 'YELLOW GREEN']

class BarPanel(XmlPanel):
  """Generate a bar graph using wx.lib.plot"""
  def __init__(self, parent,elem):
    XmlPanel.__init__(self, parent)
    self.elem = elem
    self.plot = plot.PlotCanvas(self)
    self.sizer = wx.BoxSizer(wx.VERTICAL)
    self.legendSize = 200
    
    psize = self.parent.GetSize()
    self.setSize(psize.x-30,psize.y/2)  # Start with the biggest possible size

    self.render()
    #self.sizer.Add(self.plot, 1, wx.LEFT | wx.TOP | wx.GROW)
    #self.SetSizer(self.sizer)
    #self.Fit()

  def setSize(self,x,y):
    sz = self.size = (x,y)
    self.SetInitialSize(sz)
    self.SetSize(sz)
    self.plot.SetInitialSize(sz)
    self.plot.SetSize(sz)
    

  def render(self):
    self.plot.SetBackgroundColour(None)  # None is clear
    self.plot.SetFont(wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
    self.plot.SetFontSizeAxis(10)
    self.plot.SetFontSizeLegend(7)
    self.plot.setLogScale((False, False))
    self.plot.SetXSpec('none')  # Turn off x axis grid
    self.plot.SetYSpec('auto')
    self.plot.SetEnableLegend(True)
    self.plot.SetEnableGrid(True)
    self.plot.SetEnableAntiAliasing(True)
    self.plot.SetEnableHiRes(True)

#        self.client.Redraw()
    total = len(self.elem)
    width = min(40,max(5,self.size[0]/total))

    #totalSize = width*count
    #if totalSize+self.legendSize < self.size[0]:
    #  self.setSize(totalSize+self.legendSize, self.size[1])

    count = 0
    bars = []
    for b in self.elem:
      count+=1
      legend = b.attrib.get("label",b.tag)
      points = [(count, 0), (count, float(b.text))]
      line = plot.PolyLine(points, colour=someColors[count], legend=legend, width=width)
      bars.append(line)

#    points1g = [(2, 0), (2, 4)]
#    line1g = plot.PolyLine(points1g, colour=someColors[1], legend='Mar.', width=30)


    title = self.elem.attrib.get("title", "")
    xlabel = self.elem.attrib.get("xlabel","")
    ylabel = self.elem.attrib.get("ylabel","")

    pg = plot.PlotGraphics(bars,title,xlabel,ylabel)
    self.plot.Draw(pg,xAxis=(0, count+1))
    self.plot.Show(True)
    pass


class PlotPanel(XmlPanel):
  """Draw a plot (graph)"""
  def __init__(self, parent,elem):
    XmlPanel.__init__(self, parent)
    self.border = True

    self.elem = elem
    self.figure = Figure()
    self.applySize()
    self.plot   = FigureCanvas(self,-1,self.figure)  # FancyText(self,"hi") 
    self.sizer = wx.BoxSizer(wx.VERTICAL)
    self.sizer.Add(self.plot, 1, wx.LEFT | wx.TOP | wx.GROW)
    self.SetSizer(self.sizer)
    self.Fit()
    self.render()

  def applySize(self):
    size = self.elem.attrib.get("size",None)
    if size:
      psize = self.parent.GetSize()
      try:
        size = literal_eval(size)
        size = (min(psize[0],size[0]), min(psize[1],size[1]))  # graph can't be bigger than the xmlterm
        self.SetInitialSize(size)
        self.SetSize(size)
        dpi = self.figure.get_dpi()
        self.figure.set_size_inches(float(size[0])/dpi,float(size[1])/dpi)
        # self.plot.SetSize(size)
        self.Fit()
      except ValueError,e:  # size is malformed
        print "bad size"
        pass
      return size
    return None

  def render(self):
    small = False
    size = self.applySize()
    if size and size[0]<=400:  # Small graph
      small = True

    title = None
    xlabel = None
    ylabel = None
    if not small:
      # Pull data out of the element
      title = self.elem.attrib.get("title", None)
      xlabel = self.elem.attrib.get("xlabel",None)
      ylabel = self.elem.attrib.get("ylabel",None)

    self.SetBackgroundColour(self.parent.GetBackgroundColour())
    #    self.plot.SetBackgroundColour(self.parent.GetBackgroundColour())
    bk = self.parent.GetBackgroundColour()
    colstr = "#%2x%2x%2x" % bk.Get()  # asTuple()
    self.figure.patch.set_facecolor(colstr)
    #pdb.set_trace()
    self.axes = self.figure.add_subplot(111,axisbg=colstr)
    #self.axes[0].set_label("test")
    #t = arange(0.0, 3.0, 0.01)
    #s = sin(2 * pi * t)
    #self.axes.plot(t, s)
    for child in self.elem:
      if child.tag == "series":
        data = [float(x.strip()) for x in child.text.split(",")]
        label = child.attrib.get("label",None)
        self.axes.plot(data,label=label)
        
    #ret1, = self.axes.plot([1,2,3,4,5,6,7,8],label="test_label")
    #ret2, = self.axes.plot([8,7,6,5,4,3,2,1],label="test2_label")
    if not small:
      self.axes.legend()

    # Turn off axis lines and ticks of the big subplot
    #self.axes.spines['top'].set_color('none')
    #self.axes.spines['bottom'].set_color('none')
    #self.axes.spines['left'].set_color('none')
    #self.axes.spines['right'].set_color('none')
    if small:
      # self.axes.spines['left'].set_color('none')
      self.axes.tick_params(labelcolor='none', top='off', bottom='off', left='off', right='off')
    if xlabel: self.axes.set_xlabel(xlabel)    
    if ylabel: self.axes.set_ylabel(ylabel)    
    if title: self.axes.set_title(title)

    #for axis in self.figure.axes:
    #    axis.set_title(title)
    #    axis.xaxis.set_label( "xlabel" )
    #    axis.yaxis.set_label( "ylabel" )


wildcard = "TXT files (*.txt)|*.txt|"    \
           "SVG file (*.svg)|*.svg|"        \
           "All files (*.*)|*.*"



class ProcessPanel(XmlPanel):
  """Spawn a process, get its output and send it input"""
  def __init__(self, parent,elem,resolver):
    XmlPanel.__init__(self, parent,style=wx.NO_BORDER) # wx.SIMPLE_BORDER)
    self.parent=parent
    self.resolver = resolver
    self.resolver.parentWin=self
    self.name = unescape(elem.text)
    self.cmdLine = []
    cmds = re.split("([\|\>])",self.name)
    for c in self.name.split():
      t = glob.glob(c)
      if t:
        self.cmdLine += t
      else:
        if c[0] == '"':   # Chop of a leading and trailing "
          c = c[1:-1]
        self.cmdLine.append(c)

    # print self.cmdLine
    
    self.timer = None
    self.doc = Document(self.resolver,self.onChange)
    self.process = None
    self.refreshInterval=150
    self.grabbable=True
    self.change = False
    self.keyInput=[]
    self.minSize=(100,20)
    self.size = (0,0)
    self.brush = wx.Brush(wx.Colour(*AliveColor),wx.SOLID)
    self.SetBackgroundColour(wx.Colour(*AliveColor))
    self.timerCount=0

    self.Bind(wx.EVT_PAINT, self.OnPaint)
    # Bind to handle up/down arrow and enter
    # (EVT_CHAR handles it) self.Bind(wx.EVT_KEY_DOWN, self.keyPressed)
    self.Bind(wx.EVT_TIMER, self.OnTimer)
    self.Bind(wx.EVT_CHAR, self.onCharEvent)
 
    psize = self.parent.GetSize()
    x = max(psize.x - 20, self.minSize[0])
    self.SetInitialSize((x,self.minSize[1]))
    self.SetSize((x,self.minSize[1]))

    self.timer = wx.Timer(self)
    self.timer.Start(self.refreshInterval)
    self.execute()

  def simpleString(self):
    """Returns the context of this panel as a string with no markup"""
    return self.doc.simpleString()

  def handOff(self,win,scrnPos):
    """Giving this child away -- by default let the parent deal with it"""
    self.doc.remove(win) # Remove from my document
    self.parent.handOff(win,scrnPos) # Give to my parent

  def onChange(self):
    self.change = True  # Just do it periodically to not overwhelm processor
    self.doc.layout() # a child changed so I need to layout the windows again, the child will have indicated in the doc that it needs update so layout "knows" where to look
    self.render()

  def onCharEvent(self, event):
    """A character was received.  Put it on the send queue"""
    keycode = event.GetKeyCode()
    controlDown = event.CmdDown()
    altDown = event.AltDown()
    shiftDown = event.ShiftDown()
    print "process panel got key: %d" % keycode
    if keycode<255:
      self.keyInput.append(keycode)
    self.pushInput()
 
  def pushInput(self):
    """Attempt to push anything on the send queue into the pipe, if the pipe is ready"""
    while len(self.keyInput):
      (rlist,wlist,xlist) = select.select([],[self.toChild],[],0)
      if not wlist: break  # receiver is not ready to accept any more characters
      for pipe in wlist:
        key = self.keyInput.pop(0)
        os.write(pipe,chr(key))
        

  def OnTimer(self, evt):
    """Periodically check to see if new data has been received from the child, or new data needs to be sent to the child"""
    self.timerCount+=1
    # Now see if the process is complete.  Do this before the select to ensure we get it all.
    if self.process: retCode = self.process.poll()
    else: retCode = None     

    self.doc.flush()    

    self.pushInput()

    if 1:
        # rlist = [self.fromChild]  # No we are using xmldoc feed
        rlist = []
        if self.fromChild != self.errChild:
          rlist.append(self.errChild)
        (rlist,wlist,xlist) = select.select(rlist,[],[],0)
        for pipe in rlist:
          if pipe == self.fromChild:
            pdb.set_trace()  # We are not using this code.  Instead we set up a separate thread by calling doc.startFeed()
            if 1:
              data = os.read(self.fromChild,65536 )  # self.childOut.read()
              if data:
                print "read ", data
                #self.doc.appendFragment(data)
                self.change = True
            #except OSError, e:

          elif pipe == self.errChild:
            data = os.read(self.errChild,65536) # self.childErr.read()
            print "errChild read ", data
            self.doc.append('<text fore="#ff0000">' + data + "</text>")
            self.change = True
    if self.change:
      self.change = False
      self.doc.layout()
      self.render()
      
    if retCode is not None:  # Process completed
      self.finish()

  def render(self):
    """Turn the XML or ElementTree into graphical elements"""
    sz = self.size # self.GetSize()
    # pdb.set_trace()
    self.size = self.doc.position()
    #for doce in self.doc.doc: # I have to take all my children's keys because they have all the real-estate
    #  if doce.panel: doce.panel.Bind(wx.EVT_CHAR, self.onCharEvent)
    #self.size = (max(self.size[0],self.minSize[0]),max(self.size[1],self.minSize[1]))
    self.size = (max(self.size[0],self.parent.GetSize()[0]-20),max(self.size[1],self.minSize[1]))
    # print threading.currentThread().name, sz, self.size
    if sz[0] != self.size[0] or sz[1] != self.size[1]:
      self.SetInitialSize(self.size)
      self.SetSize(self.size)
      self.parent.GetParent().relayout([self])

  def execute(self):
    """Run the process"""
    #(self.childStdin, self.toChild) = os.pipe()
    if 1: # Do it with a pseudo-tty
      (self.fromChild,self.childStdout) = os.openpty() # os.pipe()
      # (self.errChild,self.childStderr) = ( os.dup(self.fromChild),os.dup(self.childStdout))    #os.openpty() # os.pipe()
      (self.errChild,self.childStderr) = os.openpty()
      #(self.childStdin, self.toChild) = (self.childStdout, self.fromChild)
      self.toChild = os.dup(self.fromChild)
      self.childStdin = os.dup(self.childStdout)
    else: # Do it with pipes (does NOT work if the process is interactive), but "cleaner" if it is not interactive
      (self.fromChild,self.childStdout) = os.pipe()
      (self.errChild,self.childStderr) = os.pipe()
      (self.childStdin, self.toChild) = os.pipe()
      
    # Let's set all these fds to be non blocking
    if 0:
      fl = fcntl.fcntl(self.childStdout, fcntl.F_GETFL)
      fcntl.fcntl(self.childStdout, fcntl.F_SETFL, fl | os.O_NONBLOCK)
      if self.childStdout != self.childStderr:
        fl = fcntl.fcntl(self.childStderr, fcntl.F_GETFL)
        fcntl.fcntl(self.childStderr, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    if 0: # Actually we don't want it to be nonblocking because we are using a xmldoc feed...
      fl = fcntl.fcntl(self.fromChild, fcntl.F_GETFL)
      fcntl.fcntl(self.fromChild, fcntl.F_SETFL, fl | os.O_NONBLOCK)
      if self.errChild != self.fromChild:
        fl = fcntl.fcntl(self.errChild, fcntl.F_GETFL)
        fcntl.fcntl(self.errChild, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    try:
      print "executing ", self.cmdLine
      self.process = subprocess.Popen(args=self.cmdLine,stdin=self.childStdin,stdout=self.childStdout,stderr=self.childStderr,close_fds=True)
      # TODO, shouldn't we now be able to close the fds that we are not using (the child side FDs)?
      self.doc.startFeed(self.fromChild)
    except OSError, e:
      self.doc.append('<text fore="#FF0000">' + str(e) + "</text>")
      self.doc.layout()
      self.finish()    
      self.render()

  def finish(self):
    """Called when the process is complete"""
    # TODO: some visual indicator.  Maybe fade background from some "live" color to the standard background
    self.timer.Stop()
    #self.childOut.close()
    #self.childErr.close()
    os.close(self.childStdin)
    os.close(self.toChild)
    if self.childStdin != self.childStdout: os.close(self.childStdout)
    if self.childStderr != self.childStdout: os.close(self.childStderr)

    # Change the "live" background color to "dead" (parent's background color)
    self.brush = self.defaultBrush = None # wx.Brush(None,wx.SOLID)
    self.SetBackgroundColour(self.parent.GetBackgroundColour())
    self.doc.flush()
    self.render()
    self.Refresh()
    self.Update()



class SvgPanel(XmlPanel):
  """Display SVG"""
  def __init__(self, parent,elem):
      XmlPanel.__init__(self, parent) # BorderStyle)
      self.Bind(wx.EVT_PAINT, self.OnPaint)
     
      self.bmp = self.makeBitmap(elem)
      sz = self.bmp.GetSize()
      sz = (sz[0]+3,sz[1]+3)  # Add room for the border
      self.SetInitialSize(sz)
      self.SetSize(sz)  # Set the size of the text entry to the full width   

  def OnPaint(self,evt):
    XmlPanel.OnPaint(self,evt)
    dc = wx.PaintDC(self)
    dc.DrawBitmap(self.bmp,1,1,False)

  def makeBitmap(self,elem):
    text = ET.tostring(elem)  # Awkward, we have to convert the XML BACK into text so rsvg can convert it back to some object representation!
    t = svg.Svg(text)
    bk = self.parent.GetBackgroundColour()  # TODO transparent background
    bkcol = (bk[0],bk[1],bk[2])
    bitmap = t.bmp(bkcol=bkcol)
    return bitmap
    

class ListPanel(XmlPanel): # ,listmix.ColumnSorterMixin):
  def __init__(self, parent,elem):
    XmlPanel.__init__(self, parent)
    self.elem = elem
    self.list = wx.ListCtrl(self,-1,pos=(0,0), style=wx.LC_REPORT 
                                 #| wx.BORDER_SUNKEN
                                 | wx.BORDER_NONE
                                 | wx.LC_EDIT_LABELS
                                 | wx.LC_SORT_ASCENDING
                                 #| wx.LC_NO_HEADER
                                 #| wx.LC_VRULES
                                 #| wx.LC_HRULES
                                 #| wx.LC_SINGLE_SEL
                                 )
    self.list.SetBackgroundColour(self.parent.GetBackgroundColour())
    self.list.SetForegroundColour(self.parent.GetForegroundColour())

    self.update(elem)
    sz = self.list.GetBestSizeTuple()
    self.list.SetSize(sz)
    self.SetSize(sz)

  def update(self,elem):
    self.elem = elem
    self.list.ClearAll()

    columns = elem.find("columns")
    count = 0
    self.colName2Idx = {}
    for c in columns:
      info = wx.ListItem()
      info.m_mask = wx.LIST_MASK_TEXT | wx.LIST_MASK_IMAGE | wx.LIST_MASK_FORMAT
      info.m_image = -1
      info.m_format = 0
      info.m_text = c.tag
      self.list.InsertColumnInfo(count, info)
      self.colName2Idx[c.tag] = count
      count += 1
    nColumns = count
    
    data = elem.find("data")
    rowNum = -1
    for row in data:
      rowNum += 1
      #index = self.list.InsertImageStringItem(sys.maxint, data[0], self.idx1)
      colNum = -1
       
      #item = wx.ListItem()
      #item.SetId(rowNum)
      #item.SetColumn(colNum)
      #item.SetText(c.text)
       
      #self.list.InsertItem(item)
      self.list.InsertStringItem(rowNum,"") 

      for c in row:
        colNum += 1
        self.list.SetStringItem(rowNum,colNum,c.text)
        #item = wx.ListItem()
        #item.SetId(rowNum)
        #item.SetColumn(colNum)
        #item.SetText(c.text)
        #self.list.SetItem(rowNum,colNum,c.text)
        #self.list.InsertItem(item)
           
    for x in range(0,nColumns):
      self.list.SetColumnWidth(x, wx.LIST_AUTOSIZE)
   
 

class WidgetPanel(XmlPanel):
  """A widget is a collection of elements.  Widgets can be manipulated as a unit, reloaded periodically, redrawn by updating the same named widget, and extracted from the shell""" 
  def __init__(self, parent,elem,resolver):
      XmlPanel.__init__(self, parent)
      #self.parent=parent
      self.doc = None
      self.resolver = resolver
      self.resolver.parentWin=self
      try:
        self.name = elem.attrib["name"]
      except KeyError:
        self.name = None
      self.timer = None

      self.update(elem)
      self.Bind(wx.EVT_TIMER, self.OnTimer)

      self.grabbable = True

  def simpleString(self):
    """Returns the context of this panel as a string with no markup"""
    return self.doc.simpleString()

  def OnMouse(self,event):
    """Mouse control"""

    if event.RightDown(): # If you right click, context menu
      print "right down"
      self.OnContextMenu(event)
    else:  # We didn't care about this mouse event, so give it to someone else
      XmlPanel.OnMouse(self,event)

  def OnContextMenu(self, event):
        # only do this part the first time so the events are only bound once
        #
        # Yet another anternate way to do IDs. Some prefer them up top to
        # avoid clutter, some prefer them close to the object of interest
        # for clarity. 
        if not hasattr(self, "popupSave"):
            self.popupSave = wx.NewId()
            self.popupSaveWidget = wx.NewId()

            self.Bind(wx.EVT_MENU, self.OnSaveData, id=self.popupSave)
            self.Bind(wx.EVT_MENU, self.OnSaveWidget, id=self.popupSaveWidget)

        # make a menu
        menu = wx.Menu()
        if self.bdata is not None:
          text = "Save"
        else:
          text = "Not saveable (no data)" 
        # Show how to put an icon in the menu
        item = wx.MenuItem(menu, self.popupSave,text)
        #bmp = images.Smiles.GetBitmap()
        #item.SetBitmap(bmp)
        menu.AppendItem(item)
        if self.bdata is None:
          menu.Enable(self.popupSave,False)
 
        # add some other items
        menu.Append(self.popupSaveWidget, "Save Widget")

        # make a submenu
        #sm = wx.Menu()
        #sm.Append(self.popupID8, "sub item 1")
        #sm.Append(self.popupID9, "sub item 1")
        #menu.AppendMenu(self.popupID7, "Test Submenu", sm)

        # Popup the menu.  If an item is selected then its handler
        # will be called before PopupMenu returns.
        self.PopupMenu(menu)
        menu.Destroy()


  def OnSaveData(self, event):
    dlg = wx.FileDialog(self, message="Save file as ...", defaultDir=os.getcwd(), defaultFile="", wildcard=wildcard, style=wx.SAVE)

    dlg.SetFilterIndex(2)

    if dlg.ShowModal() == wx.ID_OK:
      path = dlg.GetPath()
      if self.bdata is not None:
        f = open(path,"wb")
        f.write(self.bdata.text)
        f.close()


  def OnSaveWidget(self, event):
        print("Popup two\n")



  def update(self,elem):
    """Replace the contents of this widget panel with new contents"""
    self.size = None
    self.tree = elem
    self.doc = Document(self.resolver)

    self.display = self.tree.find("display") # TODO you can have multiple displays which are chosen via attributes
    if self.display is None: assert(0)  # what to do?
    self.bdata = self.tree.find("bdata", None) # TODO: starts with bdata... This data is appropriate for cut/paste
    self.refreshElem = self.tree.find("refresh",None)
    if self.refreshElem is not None:  # This is how to get modified data
      self.refresh = self.refreshElem.text
      self.refreshInterval = int(self.refreshElem.get("interval",None))
      if self.refreshInterval:
        if self.timer: self.timer.Stop()
        else: self.timer = wx.Timer(self)
        self.timer.Start(self.refreshInterval)

    self.doc.append(self.display)
    self.doc.layout()
    self.render()

  def OnTimer(self, evt):
    # Refresh this object
    text = GetExternalEntity(self.refresh)
    if text:
      elem = ET.fromstring(text)
      self.update(elem)

  def render(self):
    """Turn the XML or ElementTree into graphical elements"""
    self.size = self.doc.position()
    self.SetSizeWH(*self.size)
    #else:  self.Fit()


class TimePanel(XmlPanel):
    def __init__(self, parent):
        XmlPanel.__init__(self, parent)
        self.clock = gizmos.LEDNumberCtrl(self, -1, (0,0), (500, 80),gizmos.LED_ALIGN_CENTER | wx.NO_BORDER)# | gizmos.LED_DRAW_FADED)
        self.clock.SetBackgroundColour(parent.GetBackgroundColour())
        self.clock.SetForegroundColour(parent.GetForegroundColour())
        self.SetBackgroundColour(parent.GetBackgroundColour())
        self.OnTimer(None)

        self.timer = wx.Timer(self)
        self.timer.Start(1000)
        self.Bind(wx.EVT_TIMER, self.OnTimer)

    def OnTimer(self, evt):
        t = time.localtime(time.time())
        st = time.strftime("%I-%M-%S", t)
        self.clock.SetValue(st)

def FancyTextChunked(parent,text,fore=None,back=None,size=None,chunkSize=4096):
  """Returns a list of windows which contain the passed text broken into pieces of approximately chunkSize.
     Chunking large text is needed because the windowing system does not perform well when rendering gigantic panels, most of which is off-screen
  """
  ret = []
  while len(text) > chunkSize:
    pos = text.find("\n",chunkSize)
    ret.append(FancyText(parent,text[0:pos],fore,back,size))
    text = text[pos+1:] # +1 because we want to skip the \n because the chunk will do so itself
  if text:
    ret.append(FancyText(parent,text,fore,back,size))
  return ret

class FancyText(XmlPanel):
  """This panel draws text in a specific color or style"""
  def __init__(self, parent,text,fore=None,back=None,size=None):
    XmlPanel.__init__(self, parent) # ,style=wx.SIMPLE_BORDER)
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.text = text
    #if type(fore) == types.TupleType:
    #  self.foregroundColor = "#%2x%2x%2x" % (fore[0],fore[1],fore[2])
    self.foregroundColor = fore
    #if type(back) == types.TupleType:
    #  self.backgroundColor = "#%2x%2x%2x" % (back[0],back[1],back[2])    
    self.backgroundColor = back
    self.size = size
    self.calcSize()

  def simpleString(self):
    """Returns the context of this panel as a string with no markup"""
    return self.getText()

  def OnPaint(self,evt):
    dc = wx.PaintDC(self)
    self.paintXmlPanel(dc)
    self.render(dc)

  def calcSize(self):
    dc = wx.ClientDC(self) # I need to prerender it to get the size
    if self.size:
      font = dc.GetFont()
      font.SetPixelSize((self.size,self.size))
      dc.SetFont(font)
    self.render(dc)

    text = self.getText()    

    (width, height, descent, externalLeading) = dc.GetFullTextExtent(text)  # TODO: I should really remove just the last \n and any spaces after it, not all of them, because the fancytext is itself a block so there is an implied CR
    sz = wx.Size(width,height)
    self.SetInitialSize(sz)
    self.SetSize(sz)  # Set the size of the text entry to the full width   
    return (width, height)
 
  def GetValue(self):
    return self.text

  def appendText(self,text):
    """Add text onto the end of this panel"""
    # TODO move all this processing into a vtText class
    lst = text.split(chr(8)) # backspaces
    lst = intersperse(lst,8)
    t = self.text

    for l in lst:
      if type(l) is types.IntType:
        if l == 8:  # Backspace, remove the last character
          t = t[0:-1]
      else:
        t = t + l
          
    self.SetValue(t)

  def getText(self):
    if type(self.text) is types.FunctionType:
      text = str(self.text())
    else:
      text = self.text.rstrip()
    return text

  def SetValue(self,text):
    t = self.getText()
    self.text = text
    newt = self.getText()
    if newt != t:
      self.calcSize()
    
  def render(self,dc):
    if self.foregroundColor:
      dc.SetTextForeground(wx.Colour(*self.foregroundColor))
    if self.selected:
      print "text %s is selected" % self.getText()
      dc.SetTextBackground(SelectedColor)
      dc.SetBackground(wx.Brush(SelectedColor,wx.SOLID))
    elif self.backgroundColor == wx.TRANSPARENT_BRUSH:
      dc.SetBackground(wx.TRANSPARENT_BRUSH)
      dc.SetTextBackground(None)
    elif self.backgroundColor:
      dc.SetTextBackground(wx.Colour(*self.backgroundColor))
      dc.SetBackground(wx.Brush(wx.Colour(*self.backgroundColor),wx.SOLID))
    else:  # None, use parent background color
      self.SetBackgroundColour(self.parent.GetBackgroundColour())
    dc.Clear()

    if self.size:
      font = dc.GetFont()
      font.SetPixelSize((self.size,self.size))
      dc.SetFont(font)

    text = self.getText()    

    dc.DrawText(text,0,0)
    sx = dc.MaxX()
    sy = dc.MaxY()
    #self.SetInitialSize(wx.Size(sx,max(height, sy)))  # You can't setSize within OnPaint or you'll get an infinite paint loop
