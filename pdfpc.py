#! /usr/bin/python

from __future__ import print_function, division

import os, sys
import time
try:
    from PyQt4 import QtGui, QtCore
except:
    print( "Requires python binding for Qt4 and poppler-Qt4" )
    sys.exit()

from doc import *
from gui import *


# TODO
#   multipage overview
#   caching ?
#   jump ?

class Application(QtGui.QApplication):
    """The root application
      * open the document
      * handles keyboard shortcuts
      * manage views
    """
    
    def __init__(self, filename):
    
        self.doc = Document(filename)
        self.freezed = None
        self.color = None
        self.current = self.doc.pages[0]
        self.current_overview = None
        
        self.first_is_master = None
        self.helping = False
        self.overview_mode = False
        self.previous_page = None
        
        self.clock_start = None
        self.clock = 0
        self.last_move_time = time.time()
        
        QtGui.QApplication.__init__(self, sys.argv)
        
        self.NO_CURSOR = QtGui.QCursor(QtCore.Qt.BlankCursor)
        self.BASE_CURSOR = QtGui.QCursor(QtCore.Qt.ArrowCursor)
        self.LINK_CURSOR = QtGui.QCursor(QtCore.Qt.PointingHandCursor)
        
        desktop = QtGui.QDesktopWidget()
        nb_screens = desktop.screenCount()
        if nb_screens > 2:
            print( "Warning: no support for more than 2 screens" )
        
        self.views = [  ]
        if nb_screens > 1:
            presenter_view = View(self, desktop,0, True,False)
            slide_view = View(self, desktop,1, False, False)
            self.views = (presenter_view, slide_view)
        else:
            main_view = View(self, desktop,0, False,True)
            self.views = (main_view, )
        
        self.keyhandler = None
        self.keymap = {}
        for short in KEYMAP:
            cb = short[0]
            for k in short[1:]:
                self.keymap[k] = cb
        
        self.just_starting()
    
    def set_current(self, page):
        self.just_starting()
        if page:
            self.current = page
            self.refresh()
        if self.overview_mode:
            self.overview()
    
    def set_current_overview(self, page):
        if not self.overview or not page:
            return
        self.current_overview = page
        self.refresh()
    
    def next(self, skip_overlay=False):
        "Go to the next slide or overlay"
        if self.overview_mode:
            return self.overview_move(False, skip_overlay)
        next = self.current.get_next(skip_overlay)
        self.set_current( next )
    
    def prev(self, skip_overlay=False):
        "Go to the previous slide or overlay"
        if self.overview_mode:
            return self.overview_move(True, skip_overlay)
        prev = self.current.get_prev(skip_overlay)
        self.set_current( prev )
    
    def forward(self):
        "Go to the next slide (skip overlays)"
        self.next(True)
    
    def backward(self):
        "Go to the previous slide (skip overlays)"
        self.prev(True)
    
    def get_slide(self):
        if self.freezed is not None:
            return self.freezed
        
        return self.current
    
    def get_current(self):
        return self.current
    
    def get_current_overview(self):
        return self.current_overview
    
    def get_next(self):
        return self.current.next
        
    def get_next_overlay(self):
        return self.current.get_next_overlay()
    
    def set_position(self, pos, overlay=0):
        if pos < 0 or overlay < 0:
            return False
        
        if pos < len(self.doc.layout):
            cur = self.doc.layout[pos]
            if overlay < cur.overlay.count:
                cur = cur.overlay.pages[overlay]
            else:
                cur = cur.overlay.pages[-1]
            self.current = cur
            return True
        
        return False
    
    
    def just_starting(self):
        "Helper to start the timer on the first move"
        if self.clock_start is None:
            self.clock_start = time.time()
            self.refresh()
            return True
    
    def get_clock(self):
        "Retrieve the current clock value and pause status"
        if self.clock_start is None:
            return self.clock,True
        extra = int( time.time() - self.clock_start )
        return self.clock+extra, False
    
    def refresh(self):
        "Trigger a redraw"
        
        # detect when to stop videos
        if self.previous_page != self.current:
            self.previous_page = self.current
            self.stop_videos()
        
        # hide the cursor if it didn't move for a while
        if self.last_move_time:
            if time.time() > self.last_move_time + 3:
                #QtGui.QApplication.setOverrideCursor(self.NO_CURSOR)
                self.last_move_time = None
        
        for v in self.views:
            v.refresh()
    
    def has_moved(self, evt, links):
        self.last_move_time = time.time()
        l = find_link(evt, links)
        if l:
            QtGui.QApplication.setOverrideCursor(self.LINK_CURSOR)
        else:
            QtGui.QApplication.setOverrideCursor(self.BASE_CURSOR)
        return l
    
    def grab_keys(self, handler):
        self.keyhandler = handler
    
    def handle_key(self, e):
        "Keyboard shortcuts: use a predefined keymap"
        if type(e) == QtGui.QKeyEvent:
            if self.helping:
                self.help()
                return
            
            key = e.key()
            if self.keyhandler:
                self.keyhandler.handle_key()
            if key in self.keymap:
                e.accept()
                callback = self.keymap[key]
                callback(self)
                return
        
        e.ignore()
    
    def switch(self):
        "Switch slide/presenter screens"
        for v in self.views:
            v.switch_mode()
    
    def pause(self):
        "Pause or unpause the timer"
        if self.just_starting():
            return
        self.clock += int( time.time() - self.clock_start )
        self.clock_start = None
        self.refresh()
    
    def freeze(self):
        "Freeze the main slide (avoid disruption while browsing)"
        # no freeze in single window mode
        if len(self.views) < 2 or self.freezed:
            self.freezed = None
        else:
            self.freezed = self.current
    
        self.refresh()
    
    def black(self):
        "Turn the main display black"
        self.trigger_color(BLACK)
    
    def white(self):
        "Turn the main display white"
        self.trigger_color(WHITE)
    
    def trigger_color(self, color):
        if color == self.color:
            self.color = None
        else:
            self.color = color
        self.refresh()
    
    def jump(self):
        "[TODO] jump to a  given slide"
        print( "TODO: jump" )
    
    def start(self):
        "Jump to the first slide"
        self.set_position(0)
        self.refresh()
    
    def reset(self):
        "Jump to the first slide and reset the clock"
        self.set_position(0)
        self.clock = 0
        self.clock_start = None
        self.refresh()
    
    def overview(self, escape=False):
        "Show a grid of slides for quick visual selection"
        if not self.overview_mode:
            self.current_overview = self.current
        else:
            if not escape and self.current_overview:
                self.current = self.current_overview
            self.current_overview = None
        self.overview_mode = not self.overview_mode
        for v in self.views:
            v.config_view()
    
    def overview_move(self, backward, vertical):
        if backward:
            next = self.current_overview.get_prev(vertical)
        else:
            next = self.current_overview.get_next(vertical)
        self.set_current_overview( next )
    
    def stop_videos(self):
        stopped = False
        for v in self.views:
            stopped = stopped or v.stop_videos()
        return stopped
    
    def video(self):
        "Play videos from the current slide"
        if self.stop_videos():
            return
        
        for v in self.views:
            v.video()
    
    def escape(self):
        "Leave modes (overview...), pause, quit the application"
        
        if self.stop_videos():
            return
        
        if self.helping:
            return self.help()
        
        if self.overview_mode:
            return self.overview(True)
        
        if self.color:
            return self.trigger_color(None)
        
        if self.freezed:
            return self.freeze()
        
        if self.clock_start:
            return self.pause()
        
        QtGui.QApplication.quit()
    
    def help(self):
        "Show shortcuts"
        self.helping = not self.helping
        for v in self.views:
            v.config_view()
    
    def get_help(self):
        return get_help()
    
    def click_map(self, evt, links):
        "Detect if a link was clicked"
        if self.helping:
            self.help()
            return
        
        l = find_link(evt, links)
        if not l:
            return
        lx,ly,lx2,ly2, target = l
        if isinstance(target, PageInfo):
            self.current = target
            if self.overview_mode:
                self.overview_mode = False
            self.refresh()
        else:
            print( "Unsupported link type?" )


def find_link(evt, links):
    if not links:
        return
    
    pos = evt.pos()
    x = pos.x()
    y = pos.y()
    
    for l in links:
        lx,ly,lx2,ly2, target = l
        if x > lx and x < lx2 and y>ly and y < ly2:
            if isinstance(target, PageInfo):
                return l


K = QtCore.Qt
A = Application
KEYMAP = [
    
    (A.next,      K.Key_Right, K.Key_Down, K.Key_Space,     K.Key_MediaNext),
    (A.prev,      K.Key_Left,  K.Key_Up,   K.Key_Backspace, K.Key_MediaPrevious),
    (A.forward,   K.Key_PageDown,),
    (A.backward,  K.Key_PageUp, ),
    
    (A.switch,    K.Key_S, ),
    
    (A.pause,     K.Key_P, ),
    (A.freeze,    K.Key_F),
    
    (A.black,     K.Key_B),
    (A.white,     K.Key_W),
    
    (A.start,     K.Key_Home, ),
    (A.reset,     K.Key_R, ),
    
    (A.help,      K.Key_H, K.Key_Question),
#    (A.jump,      K.Key_G, K.Key_J),
    (A.video,      K.Key_V, ),
    (A.overview,  K.Key_Tab, K.Key_O, ),
    
    (A.escape,    K.Key_Escape, K.Key_Q),
]
del(K)
del(A)

def get_help():
    maxname = len("Action")
    maxname = 5
    maxshort = 5
    maxdescr = 5
    keys = [ ("Action","Description","Shortcuts"), (None,None,None)]
    for short in KEYMAP:
        cb = short[0]
        l = len(cb.__name__)
        if l > maxname: maxname = l
        shorts = [ str(QtGui.QKeySequence( key ).toString()) for key in short[1:] ] 
        shorts = " ".join(shorts)
        l = len(shorts)
        if l > maxshort: maxshort = l
        
        if cb.__doc__: doc = cb.__doc__.split("\n")[0]
        else: doc = ""
        l = len(doc)
        if l > maxdescr: maxdescr = l
        keys.append( (cb.__name__, doc, shorts) )
    
    nb_lines = 2
    help = ""
    maxlen = 20
    for name,doc,shorts in keys:
        if not name:
            help_line = "-"*(maxname+maxshort+maxdescr+8)+"\n"
        else:
            skip1 = " "*(maxname-len(name))
            skip2 = " "*(maxshort- len(shorts))
            help_line = "%s%s   %s%s   %s\n" % (name, skip1, shorts, skip2,doc)
        l = len(help_line)
        if l > maxlen: maxlen = l
        help += help_line
        nb_lines += 1
    
    return help, nb_lines, maxlen


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print( "Usage: %s <filename.pdf>" % sys.argv[0] )
        print()
        print( get_help()[0] )
        print()
        sys.exit()
    
    filename = sys.argv[1]
    if not os.path.isfile(filename):
        print( filename+" is not a file" )
        sys.exit()
    
    application = Application(filename)
    sys.exit(application.exec_())


