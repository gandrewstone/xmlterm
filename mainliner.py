import wx

theEVT_EXECUTE = wx.NewEventType()
EVT_EXECUTE = wx.PyEventBinder(theEVT_EXECUTE, 1)

class ExecuteEvent(wx.PyCommandEvent):
   """Event to signal something must be run in the main thread"""
   def __init__(self, thunk):
     wx.PyCommandEvent.__init__(self, theEVT_EXECUTE, -1)
     self.thunk = thunk
     self.ResumePropagation(1000)  # propagate all the way
