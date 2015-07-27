import sys, time
import math
import os
import re
import string
import pdb
import urlparse
import urllib
import svg
from string import Template

from xml.sax.saxutils import escape,unescape

import xml.etree.ElementTree as ET

import wx.lib.scrolledpanel as scrolled
import wx.gizmos as gizmos
import wx.richtext
import wx.lib.fancytext
import wx
import wx.aui

from xmlpanels import *

dirPrompt = lambda: os.environ.get("PWD","") + ">"

class CmdLine(wx.Panel):
  """Handle command line entry.  Includes history and command completion"""
  def __init__(self, parent,execute=None,completion=None):
    wx.Panel.__init__(self, parent, style = wx.NO_BORDER)
    self.parentWin = parent
    #self.prompt = wx.StaticText(self,-1,"sp> ")
    self.font = wx.Font(16, wx.SWISS, wx.NORMAL, wx.NORMAL, False,'MS Shell Dlg 2')
    self.prompt = dirPrompt  #"XMLT> "
    self.SetFont(self.font)
    self.ENTRY_EXTRA = 8
    self.history=[""]
    self.historyPos=-1

    self.executeHandler = execute
    self.completionHandler = completion # Set this to install a command completion handler: def handler(editLine): return "completion"

    self.promptPanel = FancyText(self,self.prompt,fore=(0,0,255))

    self.entry = wx.TextCtrl(self, -1, "",style = wx.NO_BORDER) # | wx.TE_MULTILINE)  # Only 1 line but text styles are only supported in the multiline widget in wxGTK
    self.entry.SetBackgroundColour(parent.GetBackgroundColour())
    self.completionPanel= FancyText(self,"",fore=(130,130,130))

    self.Bind(wx.EVT_SIZE, self.OnSize) #here I am binding the event.

    # Bind to these to handle completion, etc
    self.entry.Bind(wx.EVT_TEXT, self.textEntryHandler)
    self.entry.Bind(wx.EVT_TEXT_ENTER, self.textEntryHandler)

    # Bind to handle up/down arrow and enter
    self.entry.Bind(wx.EVT_KEY_DOWN, self.keyPressed)

  def append(self,text):
    self.entry.AppendText(text)

  def keyPressed(self,evt):
    key = evt.GetKeyCode()
    if key=="v" or key == "V" and evt.ControlDown():  # PASTE
      if not wx.TheClipboard.IsOpened():
       wx.TheClipboard.Open()
       # success = wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP))
       clipText = wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT))
       wx.TheClipboard.Close()
       if clipText:
         self.entry.AppendText(str(clipText))
    if key==wx.WXK_F1:
      print "F1 KEY HIT"
      self.parentWin.windowMover()
    if key==wx.WXK_TAB:
      self.entry.AppendText(self.completionPanel.GetValue())
      self.completionPanel.SetValue("")
      self.entry.SetInsertionPointEnd()      
    elif key==wx.WXK_RETURN:
      entry = self.entry.GetValue()
      self.history[-1] = entry  # Overwrite the last history with what the user actually selected
      self.history.append("")  # Add a new empty line to the history
      self.entry.SetValue("");
      if self.executeHandler:
        self.executeHandler(entry)
      # TODO process this command
    elif key==wx.WXK_UP:
      if self.historyPos==-1 or self.historyPos==len(self.history)-1: self.history[-1] = self.entry.GetValue()  # If he was on the current edit line and is moving away, then save the current edit line
      self.historyPos = self.historyPos - 1
      try:
        self.entry.SetValue(self.history[self.historyPos]) # + "completion test")
        #tmp = self.entry.GetDefaultStyle()
        #self.entry.SetDefaultStyle(wx.TextAttr(wx.RED))
        #self.entry.AppendText("completion test")
        #self.entry.SetDefaultStyle(tmp)
        #result = self.entry.SetStyle(len(self.history[self.historyPos]), len(self.history[self.historyPos] + "completion test"), wx.TextAttr(wx.RED, (84, 84, 84)))
        #print result
      except IndexError, e:
        self.historyPos = -1
        self.entry.SetValue(self.history[self.historyPos])
      self.entry.SetInsertionPointEnd()
    elif key==wx.WXK_PAGEDOWN:
        self.historyPos = -1
        self.entry.SetValue(self.history[self.historyPos])
        self.entry.SetInsertionPointEnd()
    elif key==wx.WXK_DOWN:
      if self.historyPos==-1 or self.historyPos==len(self.history)-1: self.history[-1] = self.entry.GetValue()  # If he was on the current edit line and is moving away, then save the current edit line
      self.historyPos = self.historyPos + 1
      try:
        self.entry.SetValue(self.history[self.historyPos])
      except IndexError, e:
        self.historyPos = -1
        self.entry.SetValue(self.history[self.historyPos])
      self.entry.SetInsertionPointEnd()
    else:
      evt.Skip()  # This means that I did not handle the event, find another handler
    #print key

  def textEntryHandler(self,evt):
    value = self.entry.GetValue()
    if self.completionHandler:
      completion = self.completionHandler(value)
      self.completionPanel.SetValue(completion)
    #print value
    (px,py) = self.promptPanel.GetBestSizeTuple()
    entryX,entryY = self.entry.GetTextExtent(value)
    self.completionPanel.MoveXY(px+entryX+self.ENTRY_EXTRA,0)  # But drop the completion panel on top of it

    #self.refresh()  # I need to move the windows around based on the changing content

  def refresh(self):
    (x,py) = self.promptPanel.GetBestSizeTuple()
    entryX,entryY = self.entry.GetTextExtent(self.entry.GetValue())
    y = max(py,entryY)
    promptPos = self.promptPanel.GetPosition()
    if promptPos[0] != 0 or promptPos[1] != (y-py)/2:
      self.promptPanel.MoveXY(0,(y-py)/2)
    entryPos = self.entry.GetPosition()
    if entryPos[0] != x or entryPos[1] != 0:
      self.entry.MoveXY(x,0)

    pSize = self.parentWin.GetClientSizeTuple()
 
    entrySz = self.entry.GetSize()
    mySz = self.GetSize()
  
    if entrySz.x != pSize[0]-x:
      self.entry.SetSizeWH(pSize[0]-x,-1)  # Set the size of the text entry to the full width
      self.entry.SetFocus()  # This causes the command line to get the keyboard events whenever the LiveDoc is selected (otherwise you need to click on it explicitly)
      self.completionPanel.MoveXY(x+entryX+self.ENTRY_EXTRA,0)  # But drop the completion panel on top of it
    if mySz.x != pSize[0] or mySz.y != y:  
      self.SetSizeWH(pSize[0],y)
    return y
   

  def OnSize(self,event):
    self.refresh()
    pass
