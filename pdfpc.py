#! /usr/bin/python

from __future__ import print_function, division

import os, sys
import time
try:
    from PyQt4 import QtGui, QtCore
    import popplerqt4
except:
    print( "Requires python binding for Qt4 and poppler-Qt4" )
    sys.exit()


# TODO
#   multipage overview
#   caching ?
#   jump ?
#   video support ?

class Application(QtGui.QApplication):
    """The root application
      * open the document
      * handles keyboard shortcuts
      * manage views
    """
    
    def __init__(self, filename):
    
        try:
            self.doc = Document(filename)
        except:
            print( "Error loading the file" )
            sys.exit()
        
        self.cur_page = 0
        self.first_is_master = None
        self.helping = False
        self.debug = False
        
        self.clock_start = None
        self.clock = 0
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.tick)
        self.last_move_time = time.time()
        
        QtGui.QApplication.__init__(self, sys.argv)
        
        self.NO_CURSOR = QtGui.QCursor(QtCore.Qt.BlankCursor)
        self.BASE_CURSOR = QtGui.QCursor(QtCore.Qt.ArrowCursor)
        self.LINK_CURSOR = QtGui.QCursor(QtCore.Qt.PointingHandCursor)
        
        self.presenter = Presenter(self)
        self.slide = Slide(self)
        self.switch()
        self.keymap = {}
        for short in KEYMAP:
            cb = short[0]
            for k in short[1:]:
                self.keymap[k] = cb
    
    def just_starting(self):
        "Helper to start the timer on the first move"
        if self.clock_start is None:
            self.clock_start = time.time()
            self.refresh(False)
            self.timer.start(1000)
            return True
    
    def get_clock(self):
        "Retrieve the current clock value and pause status"
        if self.clock_start is None:
            return self.clock,True
        extra = int( time.time() - self.clock_start )
        return self.clock+extra, False
    
    def refresh(self, full=True):
        "Trigger a redraw"
        
        # hide the cursor if it didn't move for a while
        if self.last_move_time:
            if time.time() > self.last_move_time + 3:
                QtGui.QApplication.setOverrideCursor(self.NO_CURSOR)
                self.last_move_time = None
        
        self.presenter.refresh(full)
        self.slide.refresh(full)
    
    def has_moved(self, evt, links):
        self.last_move_time = time.time()
        l = find_link(evt, links)
        if l:
            QtGui.QApplication.setOverrideCursor(self.LINK_CURSOR)
        else:
            QtGui.QApplication.setOverrideCursor(self.BASE_CURSOR)
        return l
    
    def handle_key(self, e):
        "Keyboard shortcuts: use a predefined keymap"
        if type(e) == QtGui.QKeyEvent:
            key = e.key()
            if key in self.keymap:
                e.accept()
                callback = self.keymap[key]
                callback(self)
                return
        
        e.ignore()
    
    def switch(self):
        "Switch slide/presenter screens"
        desktop = QtGui.QDesktopWidget()
        nb_screens = desktop.screenCount()
        if nb_screens > 2:
            print( "Warning: no support for more than 2 screens" )
        
        if self.first_is_master is None:
            self.first_is_master = True
        elif self.first_is_master:
            self.first_is_master = False
        else:
            self.first_is_master = True
        
        if self.first_is_master:
            place_view(self.presenter, desktop, 0)
            place_view(self.slide, desktop, 1)
        else:
            place_view(self.presenter, desktop, 1)
            place_view(self.slide, desktop, 0)
        
        self.refresh()
    
    def pause(self):
        "Pause or unpause the timer"
        if self.just_starting():
            return
        self.timer.stop()
        self.clock += int( time.time() - self.clock_start )
        self.clock_start = None
        self.refresh(False)
    
    def freeze(self):
        "Freeze the main slide (avoid disruption while browsing)"
        self.doc.freeze()
        self.refresh()
    
    def black(self):
        "Turn the main display black"
        self.doc.trigger_color(BLACK)
        self.refresh()
    
    def white(self):
        "Turn the main display white"
        self.doc.trigger_color(WHITE)
        self.refresh()
    
    def tick(self):
        self.refresh(False)
    
    def next(self):
        "Go to the next slide or overlay"
        if self.just_starting():
            return
        if self.doc.next():
            self.refresh()
    
    def prev(self):
        "Go to the previous slide or overlay"
        if self.just_starting():
            return
        if self.doc.prev():
            self.refresh()

    def forward(self):
        "Go to the next slide (skip overlays)"
        if self.just_starting():
            return
        if self.doc.next(True):
            self.refresh()
    
    def backward(self):
        "Go to the previous slide (skip overlays)"
        if self.just_starting():
            return
        if self.doc.prev(True):
            self.refresh()
    
    def jump(self):
        "[TODO] jump to a  given slide"
        print( "TODO: jump" )
    
    def start(self):
        "Jump to the first slide"
        self.doc.set_position(0)
        self.refresh()
    
    def reset(self):
        "Jump to the first slide and reset the clock"
        self.doc.set_position(0)
        self.clock = 0
        self.clock_start = None
        self.refresh()
    
    def overview(self):
        "Show a grid of slides for quick visual selection"
        self.presenter.overview_mode = not self.presenter.overview_mode
        self.presenter.refresh()
    
    def escape(self):
        "Leave modes (overview...), pause, quit the application"
        if self.helping:
            self.help()
            return
        
        if self.presenter.overview_mode:
            self.overview()
            return
        
        if self.doc.color:
            self.doc.trigger_color(None)
            self.refresh()
            return
        
        if self.doc.freezed:
            self.freeze()
            return
        
        if self.clock_start:
            self.pause()
            return
        
        QtGui.QApplication.quit()
    
    def help(self):
        "Show shortcuts"
        self.helping = not self.helping
        self.refresh()
    
    def click_map(self, evt, links):
        "Detect if a link was clicked"
        l = find_link(evt, links)
        if not l:
            return
        lx,ly,lx2,ly2, target = l
        if isinstance(target, PageInfo):
            self.doc.current = target
            if self.presenter.overview_mode:
                self.presenter.overview_mode = False
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


def place_image(qpainter, info, x,y,w,h, links=None, linkPaint=None, note=False):
    "Paint a page info centered in the selected area"
    if info:
        image = info.get_image(w,h, note)
        size = image.size()
        iw = size.width()
        ih = size.height()
        if iw < w:
            x += (w-iw)/2
        if ih < h:
            y += (h-ih)/2
        qpainter.drawImage(x,y, image)
        
        if links is None:
            return
        
        if linkPaint:
            qpainter.setBrush(linkPaint)
        
        for l in info.get_links():
            ax = x + iw * l.x
            ay = y + ih * l.y
            aw = iw * l.w
            ah = ih * l.h
            links.append( (ax,ay,ax+aw,ay+ah, l.page) )
            if linkPaint:
                qpainter.drawRect(ax,ay, aw,ah)


def place_view(view, desktop, idx):
    "[UNTESTED] Place the selected view fullscreen on the selected monitor"
    nb_screens = desktop.screenCount() 
    if idx >= nb_screens:
        view.hide()
    else:
        view.showFullScreen()
        view.setGeometry( desktop.screenGeometry(idx) )
    view.setup()

def show_progress(qp, x,y, w,h, cur, total):
    if cur < 1 or cur >= total:
        return
    
    pw = w*cur/total
    qp.setBrush(ICON)
    qp.drawRect(x,y,w,h)
    qp.setBrush(COLD)
    qp.drawRect(x,y,pw,h)


class Presenter(QtGui.QFrame):
    """The presenter view:
        * curent slides
        * next slide and overlays
        * timer
        * overview mode
        * status indicators (paused, frozen)
    """
    
    def __init__(self, app):
        super(Presenter, self).__init__()
        self.app = app
        self.doc = app.doc
        self.setGeometry(300, 300, 1000, 800)
        self.setWindowTitle('Simple PDF presenter')
        self.cachedSize = None
        self.full_repaint = True
        self.link_map = None
        self.overview_mode = False
        self.setMouseTracking(True)
    
    def setup(self):
        size = self.size()
        self.cachedSize = size
        
        width = size.width()
        height = size.height()
        
        # pick settings for the overview
        n = len(self.doc.layout)
        onx = 3
        ony = 2
        while n > onx*ony:
            if ony < onx:
                ony += 1
            else:
                onx += 1
            if onx > 5:
                break
        
        r_overview = (0,0, width,height, onx, ony, 10)
        
        margin = 10
        width  -= 2*margin
        height -= 2*margin
        
        w_cur = 2*width/3
        h_cur= 4*height/5
        h_next = 2*height/5
        r_cur = (margin,margin, w_cur, h_cur)
        r_next = (w_cur+2*margin, margin+h_next, width/3, height/3)
        r_over = (w_cur+2*margin, margin/2, width/3, height/3)
        
        icon_m = 20
        icon_w = 3*height/20
        icon_top = height - icon_w
        h_progress = icon_w / 10
        r_progress = (0,height-h_progress+margin, width, h_progress)
        icon_w -= h_progress
        r_timer = (icon_m+2*(icon_m+icon_w), icon_top, width-4*icon_w, icon_w)
        r_paused = (width-icon_w, icon_top, icon_w, icon_w, icon_m)
        
        # detect DPI to select the proper font size
        dpi = QtGui.QDesktopWidget().physicalDpiX()
        font_scale = dpi / 96
        font_size = min(r_timer[2] / 10, 3*r_timer[3]/4)
        font_size = icon_w - 3*icon_m
        self.font = QtGui.QFont('Sans', font_size/font_scale)
        self.debug_font = QtGui.QFont('Sans', font_size/font_scale/10)
        
        r_colored = (icon_m, icon_top, icon_w, icon_w, icon_m)
        r_frozen = (2*icon_m+icon_w, icon_top, icon_w, icon_w, icon_m)
        
        
        self.layout = {
            "cur": r_cur,
            "over": r_over,
            "next": r_next,
            "timer": r_timer,
            "paused": r_paused,
            "frozen": r_frozen,
            "colored": r_colored,
            "progress": r_progress,
            "overview": r_overview,
        }
    
    def keyPressEvent(self, e):
        self.app.handle_key(e)
    
    def mouseMoveEvent(self, e):
        l = self.app.has_moved(e, self.link_map)
    
    def refresh(self, full=True):
        if full:
            self.full_repaint = True
        self.update()
    
    def repaint(self):
        size = self.size()
        width = size.width()
        height = size.height()
        if size != self.cachedSize:
            self. setup()
            self.full_repaint = True
        
        qp = QtGui.QPainter()
        qp.begin(self)
        if self.overview_mode:
            self.paint_overview(qp, width, height)
        else:
            self.paint_presenter(qp, width, height)
        
        if self.app.helping:
            show_help(qp, width, height)
        
        qp.end()
    
    def paint_presenter(self, qp, width, height):
        # partial repaints are not yet working: widget is painted in grey first
        if True or self.full_repaint:
            self.link_map = []
            self.full_repaint = False
            # background
            qp.setBrush(BG)
            qp.drawRect(0, 0, width, height)
            
            x,y,w,h = self.layout["cur"]
            info = self.doc.get_current()
            if self.app.debug:
                linkPaint = LINK
            else:
                linkPaint = None
            place_image(qp, info, x,y,w,h, self.link_map, linkPaint)
            if self.app.debug:
                qp.setPen(COLD)
                qp.setFont(self.debug_font)
                qp.drawText(x,y,w,h, QtCore.Qt.AlignCenter, info.label)
            
            x,y,w,h = self.layout["over"]
            if info.has_note:
                note=True
                o_info = info
            else:
                o_info = self.doc.get_next_overlay()
                note=False
            if o_info:
                place_image(qp, o_info, x,y,w,h, note=note)
                self.link_map.append( (x,y,x+w,y+h, o_info) )
            
            x,y,w,h = self.layout["next"]
            n_info = self.doc.get_next()
            if n_info:
                place_image(qp, n_info, x,y,w,h)
                self.link_map.append( (x,y,x+w,y+h, n_info) )
        
        
        x,y,w,h = self.layout["timer"]
        qp.setPen(TEXT)
        qp.setFont(self.font)
        seconds,paused = self.app.get_clock()
        minutes = seconds / 60
        seconds %= 60
        hours = minutes / 60
        minutes %= 60
        timetext = "%02d:%02d:%02d" % (hours,minutes,seconds)
        qp.drawText(x,y,w,h, QtCore.Qt.AlignCenter, timetext)
        
        if paused:
            x,y,w,h,m = self.layout["paused"]
            qp.setBrush(ICON)
            qp.drawEllipse(x,y,w,h)
            qp.setBrush(BG)
            dx = w/20
            bw = w/4 - dx
            bh = 3*h/5
            qp.drawRect(x+w/4, y+h/5, bw, bh)
            qp.drawRect(x+w/2+dx, y+h/5, bw, bh)
        
        margin = 10
        if self.doc.freezed:
            x,y,w,h,m = self.layout["frozen"]
            qp.setBrush(ICON)
            qp.drawEllipse(x,y,w,h)
            qp.setPen(COLD)
            qp.drawText(x+m,y+m,w-2*m,h-2*m, QtCore.Qt.AlignCenter, FROZEN)
        
        if self.doc.color:
            x,y,w,h,m = self.layout["colored"]
            qp.setBrush(ICON)
            qp.drawRect(x,y,w,h)
            qp.setBrush(self.doc.color)
            qp.drawRect(x+m,y+m,w-2*m,h-2*m)

        x,y,w,h = self.layout["progress"]
        show_progress(qp, x,y, w,h, self.doc.get_current().n+1, len(self.doc.layout))
    
    
    def paint_overview(self, qp, width, height):
        # TODO: multipage overview
        #  * shift starting point
        #  * show page indocators
        n = len(self.doc.layout)
        start = 0
        
        qp.setBrush(BG)
        qp.drawRect(0, 0, width, height)
        x,y,w,h, onx, ony, m = self.layout["overview"]
        
        dx = w / onx
        mw = dx-m
        
        dy = h/ony
        mh = dy-m
        
        mm = m/2
        cury = y+mm
        i = start
        self.link_map = []
        for line in xrange(ony):
            curx = x+mm
            for col in xrange(onx):
                
                if i >= n:
                    break
                info = self.doc.layout[i]
                place_image(qp, info, curx,cury,mw,mh)
                self.link_map.append( (curx,cury,curx+mw,cury+mh, info) )
                i += 1
                curx += dx
            cury += dy
    
    def paintEvent(self, e):
        self.repaint()
    
    def mouseReleaseEvent(self, evt):
        self.app.click_map(evt, self.link_map)


class Slide(QtGui.QFrame):
    """The main slide view, which only displays the current slide
    """
    
    def __init__(self, app):
        super(Slide, self).__init__()
        self.app = app
        self.doc = app.doc
        self.link_map = None
        self.initUI()
        self.setMouseTracking(True)
    
    def initUI(self):
        self.setGeometry(300, 300, 1000, 800)
        self.setWindowTitle('PDF View')
    
    def keyPressEvent(self, e):
        self.app.handle_key(e)
    
    def mouseMoveEvent(self, e):
        l = self.app.has_moved(e, self.link_map)
    
    def setup(self):
        pass
    
    def refresh(self, full=True):
        self.update()
    
    def repaint(self):
        size = self.size()
        width = size.width()
        height = size.height()
        
        qp = QtGui.QPainter()
        qp.begin(self)
        
        if self.doc.color:
            qp.setBrush(self.doc.color)
            qp.drawRect(0, 0, width, height)
        else:
            # black background
            qp.setBrush(BG)
            qp.drawRect(0, 0, width, height)
            
            self.link_map = []
            info = self.doc.get_slide()
            place_image(qp, info, 0,0, width,height, self.link_map, LINK_N)
        
        qp.end()
    
    def paintEvent(self, e):
        self.repaint()
    
    def mouseReleaseEvent(self, evt):
        self.app.click_map(evt, self.link_map)



class Document:
    """The document wrapper:
        * load the file
        * provides a list of pages
        * remember the current and frozen pages
    """
    
    def __init__(self, filename):
        self.doc = popplerqt4.Poppler.Document.load(filename)
        self.lastPage = self.doc.numPages()
        
        self.note_vertical = False
        self.note_horizontal = False
        self.note_first = False
        self.note_end = False
        
        if filename.endswith(".right.pdf"):
            self.note_horizontal = True
        elif filename.endswith(".left.pdf"):
            self.note_horizontal = True
            self.note_first = True
        elif filename.endswith(".bottom.pdf"):
            self.note_vertical = True
        elif filename.endswith(".top.pdf"):
            self.note_vertical = True
            self.note_first = True
        elif filename.endswith(".end.pdf"):
            # the second half of pages are note pages (LibreOffice export)
            self.note_end = True
            self.lastPage /= 2
        elif filename.endswith(".notes.pdf"):
            # note pages in between regular pages
            pass
        
        if NOTE_LABEL is None or self.note_horizontal or self.note_vertical or self.note_end:
            search_note = False
        else:
            search_note = True
        
        # detect overlays and inline note pages
        prev = None
        o_prev = None
        o_start = None
        self.layout = []
        self.pages = []
        for p in xrange(self.lastPage):
            page = self.doc.page(p)
            if search_note and page.label() == NOTE_LABEL:
                prev.set_note_page(page)
                self.pages.append(None)
                continue
            info = PageInfo(self, page, prev)
            prev = info
            self.pages.append(info)
            if info.o_prev is None:
                self.layout.append(info)
            
            if self.note_end:
                notepage = self.doc.page(p+self.lastPage)
                prev.set_note_page(notepage)
        
        # intial state
        self.freezed = None
        self.color = None
        self.current = self.pages[0]
        
        # enable anti aliasing
        self.doc.setRenderHint(popplerqt4.Poppler.Document.TextAntialiasing)
        self.doc.setRenderHint(popplerqt4.Poppler.Document.Antialiasing)
    
    def trigger_color(self, color):
        if color == self.color:
            self.color = None
        else:
            self.color = color
    
    def set_position(self, pos, overlay=0):
        if pos < 0 or overlay < 0:
            return False
        
        if pos < len(self.layout):
            cur = self.layout[pos]
            for i in xrange(overlay):
                if not cur.o_next:
                    break
                cur = cur.o_next
            self.current = cur
            return True
        
        return False
    
    def freeze(self):
        if self.freezed is None:
            self.freezed = self.current
        else:
            self.freezed = None
    
    def next(self, skip_overlay=False):
        if not skip_overlay and self.current.o_next:
            self.current = self.current.o_next
            return True
        if self.current.next:
            self.current = self.current.next
            return True
        
        return False
    
    def prev(self, skip_overlay=False):
        if skip_overlay and self.current.o_start:
            self.current = self.current.o_start
            return True
        if self.current.o_prev:
            self.current = self.current.o_prev
            return True
        if self.current.prev:
            self.current = self.current.prev
            return True
        return False
    
    def get_slide(self):
        if self.freezed is not None:
            return self.freezed
        
        return self.current
    
    def get_current(self):
        return self.current
    
    def get_next(self):
        return self.current.next
        
    def get_next_overlay(self):
        return self.current.o_next
    
    def get_page_info(self, p,o):
        pass


class PageInfo:
    """Information about a specific page:
        * size
        * links
        * provides an image of the desired size
    """
    
    def __init__(self, doc, page, prev):
        self.page = page
        self.doc = doc
        self.label = page.label()
        
        # no known successor yet
        self.next = None
        self.o_next = None
        
        # build linked list as we visit new pages
        if not prev or prev.label != self.label:
            # adding a new logical page
            self.n = len(doc.layout)
            if prev and prev.o_start:
                self.prev = prev.o_start
            else:
                self.prev = prev
            self.o_prev = None
            self.o_start = None
            # adding self as next page for the previous overlay
            while prev:
                prev.next = self
                prev = prev.o_prev
        else:
            # Adding to the same overlay
            self.n = prev.n
            prev.o_next = self
            self.prev = prev.prev
            self.o_prev = prev
            if prev.o_start is None:
                self.o_start = prev
            else:
                self.o_start = prev.o_start
        
        self.links = None
        size = self.page.pageSize()
        x,y,w,h = 0,0,  size.width(), size.height()
        
        self.note_box = None
        self.note_page = None
        if doc.note_horizontal:
            w /= 2
            if doc.note_first:
                x = w
                self.note_box = (0,0,w,h)
            else:
                self.note_box = (w,0,w,h)
        elif doc.note_vertical:
            h /= 2
            if doc.note_first:
                y = h
                self.note_box = (0,0,w,h)
            else:
                self.note_box = (0,h,w,h)
        self.bbox = (x,y,w,h)
        self.has_note = self.note_box != None
    
    def set_note_page(self, page):
        self.note_page = page
        self.has_note = True
    
    def get_links(self):
        if self.links is None:
            # discover page links
            self.links = []
            for link in self.page.links():
                area = link.linkArea()
                x = area.x()
                y = area.y()
                w = area.width()
                h = area.height()
                if isinstance(link, popplerqt4.Poppler.LinkGoto):
                    p_idx = link.destination().pageNumber() - 1
                    if p_idx < 0 or p_idx >= self.doc.lastPage:
                        print( "invalid link target: ", p_idx )
                        continue
                    page = self.doc.pages[ p_idx ]
                    self.links.append( Link(x,y,w,h, page) )
                elif isinstance(link, popplerqt4.Poppler.LinkAction):
                    # TODO: action links (used by beamer)
                    #print( "Action link: ", link.actionType() )
                    pass
                else:
                    # other types of links to support?
                    #print( type(link) )
                    pass
        
        return self.links
    
    def get_prev(self):
        if self.n_page > 0:
            return 
    
    def get_image(self, width, height, note=False):
        # TODO: cache image?
        # decide of DPI based on page and widget sizes
        page = self.page
        if note:
            if self.note_page:
                page = self.note_page
                x,y,w,h = self.bbox
            elif not self.note_box:
                return
            else:
                x,y,w,h = self.note_box
        else:
            x,y,w,h = self.bbox
        
        wratio = float(width) / w
        hratio = float(height) / h
        scale = min(wratio, hratio)
        dpi = 72 * scale
        
        x *= scale
        y *= scale
        w *= scale
        h *= scale
        
        # render page as image
        return page.renderToImage(dpi, dpi, x, y, w,h)

class Link:
    def __init__(self, x,y,w,h, page):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.page = page
        
        if self.w < 0:
            self.x += w
            self.w = -w
        if self.h < 0:
            self.y += h
            self.h = -h


# colors
BLACK   = QtGui.QColor(0, 0, 0)
WHITE   = QtGui.QColor(255, 255, 255)

HELP_BG   = QtGui.QColor(30, 30, 30, 220)

BG   = BLACK
TEXT = WHITE
DIM  = QtGui.QColor(50, 50, 50, 100)
COLD = QtGui.QColor(100, 100, 200)
ICON  = QtGui.QColor(150, 150, 150)

LINK = QtGui.QColor(200, 50, 50, 50)
LINK_N = QtGui.QColor(50, 50, 200, 50)
LINK_N = None


PAUSE = "P"
FROZEN = "F"

NOTE_LABEL = "0"

K = QtCore.Qt
A = Application
KEYMAP = [
    
    (A.next,      K.Key_Right, K.Key_Space, K.Key_MediaNext),
    (A.prev,      K.Key_Left, K.Key_Backspace, K.Key_MediaPrevious), 
    (A.forward,   K.Key_Down, K.Key_PageDown,),
    (A.backward,  K.Key_Up, K.Key_PageUp, ),
    
    (A.switch,    K.Key_S, ),
    
    (A.pause,     K.Key_P, ),
    (A.freeze,    K.Key_F),
    
    (A.black,     K.Key_B),
    (A.white,     K.Key_W),
    
    (A.start,     K.Key_Home, ),
    (A.reset,     K.Key_R, ),
    
    (A.help,      K.Key_H, K.Key_Question),
#    (A.jump,      K.Key_G, K.Key_J),
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
        doc = cb.__doc__.split("\n")[0]
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

def show_help(qp, width, height):
    help, n,l = get_help()
    qp.setBrush(HELP_BG)
    qp.setPen(WHITE)
    margin = min(width,height) / 10
    qp.drawRect(margin/2, margin/2, width-margin, height-margin)

    # pick font size
    dpi = QtGui.QDesktopWidget().physicalDpiX()
    font_scale = dpi / 96
    font_size = min(width/(l+4), height/(n+8)) / font_scale
    help_font = QtGui.QFont('Mono', font_size)
    
    qp.setFont(help_font)
    qp.drawText(margin,margin,width-2*margin,height-2*margin,
         QtCore.Qt.AlignLeft, help)


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


