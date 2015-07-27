import sys
import math
import os
import re
import string
import pdb
from xml.dom import minidom
from string import Template

import wx
import wx.lib.wxcairo
import cairo
import rsvg

def SvgFile(filename):
  filename = common.fileResolver(filename)
  f = open(filename,"r")
  data = f.read()
  f.close()
  return Svg(data)

def opt(fn):
  try:
    ret = fn()
    return ret
  except:
    return ""

class Svg:
  def __init__(self, data,svgSize=None):
    self.rawsvg = data
    self.size = svgSize  # This is a workaround because rsvg does not have get_dimensions()
 
  def prep(self,size=None):
    data = self.rawsvg
    hdl = rsvg.Handle()
    hdl.write(data)
    hdl.close()
    svgSize = (hdl.get_property('width'), hdl.get_property('height'))
    if size is None or size == svgSize or svgSize[0] <= 0 or svgSize[1] <= 0:
      size = svgSize
      scale = (1.0,1.0)
    else:
      frac = min( float(size[0])/svgSize[0], float(size[1])/svgSize[1] )
      scale = (frac, frac)  # We don't want it to be distorted
      size = (int(math.ceil(svgSize[0]*frac)), int(math.ceil(svgSize[1]*frac))) # allocate the smallest buffer that fits the image dimensions < the provided size
    return (hdl,size,scale)    

  def bmp(self, size=None, bkcol=(230,230,230,wx.ALPHA_OPAQUE)):
    """Return a bitmap.  Using cairo is preferred, but this is useful for things like buttons"""
    (hdl,size,scale) = self.prep(size)
    dc = wx.MemoryDC()
    bitmap = wx.EmptyBitmap(size[0],size[1])
    dc.SelectObject(bitmap)
    dc.SetBackground(wx.Brush(wx.Colour(*bkcol)))  # Note, I don't think bitmap supports alpha
    dc.SetBackgroundMode(wx.TRANSPARENT)
    dc.Clear()
    ctx = wx.lib.wxcairo.ContextFromDC(dc)
    ctx.scale(*scale)
    hdl.render_cairo(ctx)
    del ctx
    del dc
    return bitmap 

  def instantiate(self, size=None):
    (hdl,size,scale) = self.prep(size)
    image = cairo.ImageSurface(cairo.FORMAT_ARGB32,size[0],size[1])
    cr = cairo.Context(image)
    cr.set_source_rgba(0,0,0,0)
    cr.paint()
    cr.scale(*scale)
    hdl.render_cairo(cr)
    del hdl
    return image

def blit(ctx, bmp, location, scale=(1,1), rotate=0):
  ctx.save()
  ctx.translate(*location)
  ctx.rotate(rotate)
  ctx.scale(*scale)
  ctx.set_source_surface(bmp,0,0)
  ctx.paint()
  ctx.restore()
  
