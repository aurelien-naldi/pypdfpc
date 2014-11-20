#! /usr/bin/python

from __future__ import print_function, division

import os, sys
import time
try:
    from PyQt4 import QtGui, QtCore
    from PyQt4.phonon import Phonon
    import popplerqt4
except:
    print( "Requires python binding for Qt4 and poppler-Qt4" )
    sys.exit()


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
        
        self.first_is_master = None
        self.helping = False
        self.overview_mode = False
        self.debug = False
        self.previous_page = None
        
        self.clock_start = None
        self.clock = 0
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.tick)
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
        
        self.keymap = {}
        for short in KEYMAP:
            cb = short[0]
            for k in short[1:]:
                self.keymap[k] = cb
        
        self.just_starting()
    
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
        
        # detect when to stop videos
        if self.previous_page != self.doc.current:
            self.previous_page = self.doc.current
            self.stop_videos()
        
        # hide the cursor if it didn't move for a while
        if self.last_move_time:
            if time.time() > self.last_move_time + 3:
                QtGui.QApplication.setOverrideCursor(self.NO_CURSOR)
                self.last_move_time = None
        
        for v in self.views:
            v.refresh(full)
    
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
        for v in self.views:
            v.presenter_mode = not v.presenter_mode
        
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
        # no freeze in single window mode
        if len(self.views) < 2:
            return
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
        self.just_starting()
        if self.doc.next():
            self.refresh()
    
    def prev(self):
        "Go to the previous slide or overlay"
        self.just_starting()
        if self.doc.prev():
            self.refresh()

    def forward(self):
        "Go to the next slide (skip overlays)"
        self.just_starting()
        if self.doc.next(True):
            self.refresh()
    
    def backward(self):
        "Go to the previous slide (skip overlays)"
        self.just_starting()
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
        self.overview_mode = not self.overview_mode
        self.refresh()
    
    def stop_videos(self):
        stopped = False
        for v in self.views:
            stopped = stopped or v.stop_videos()
        return stopped
    
    def video(self):
        "Play videos from the current slide"
        if self.stop_videos():
            return
        
        for x,y,w,h,url,data in self.doc.current.get_movies():
            if url and not os.path.isfile(url):
                print( "external video not found" )
                url = None
            
            if not url and not data:
                continue
            
            for v in self.views:
                v.video(x,y,w,h, url,data)
        
    def escape(self):
        "Leave modes (overview...), pause, quit the application"
        
        if self.stop_videos():
            return
        
        if self.helping:
            self.help()
            return
        
        if self.overview_mode:
            self.overview_mode = False
            self.refresh()
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
        if self.helping:
            self.help()
            return
        
        l = find_link(evt, links)
        if not l:
            return
        lx,ly,lx2,ly2, target = l
        if isinstance(target, PageInfo):
            self.doc.current = target
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


def place_image(qpainter, info, x,y,w,h, links=None, linkPaint=None, note=False, align=0, view=None):
    "Paint a page info properly aligned in the selected area"
    if info:
        image = info.get_image(w,h, note)
        size = image.size()
        iw = size.width()
        ih = size.height()
        if align == 0:
            # center it
            if iw < w:
                x += (w-iw)/2
            if ih < h:
                y += (h-ih)/2
        elif align == 1:
            # align bottom/right
            if iw < w:
                x += w-iw
            if ih < h:
                y += h-ih
        qpainter.drawImage(x,y, image)
        
        if view:
            # remember the image position
            view.slide_position = (x,y,iw,ih)
        
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


def show_progress(qp, x,y, w,h, cur, total):
    if total < 2 or cur < 1 or cur > total:
        return
    
    
    if w > h:
        # horizontal bar
        pw = w*cur/total
        dw = w/total
        dx = x + pw - dw
        ph = h
        dh = h
        dy = y
    else:
        # vertical bar: first try dashed mode
        
        # size of points and space in dashed mode
        point_size = 3*w
        space_size = 2*w
        skip = point_size+space_size
        dashed_needed = total * skip
        if dashed_needed < 3*h/4:
            # render in dashed mode
            cur -= 1
            y += (h - dashed_needed) / 2
            qp.setBrush(ICON)
            for i in xrange(total):
                if i == cur:
                    qp.setBrush(SEL)
                    qp.drawRect(x,y,w,point_size)
                    qp.setBrush(ICON)
                else:
                    qp.drawRect(x,y,w,point_size)
                
                y += skip
            return
        
        pw = w
        dw = w
        dx = x
        ph = h*cur/total
        dh = h/total
        dy = y + ph - dh
    
    qp.setBrush(ICON)
    qp.drawRect(x,y,w,h)
    qp.setBrush(COLD)
    qp.drawRect(x,y,pw,ph)
    
    qp.setBrush(HG)
    qp.drawRect(dx,dy,dw,dh)


class View(QtGui.QFrame):
    """The view, with 3 modes:
        * presenter console:
            * curent slide
            * next slide, overlays, notes
            * timer
            * status indicators (paused, frozen)
        * overview mode (list of slides)
        * main view (only the current slide)
    """
    
    def __init__(self, app, desktop_info, target_desktop, is_presenter, is_single):
        super(View, self).__init__()
        self.app = app
        self.doc = app.doc
        self.setWindowTitle('Simple PDF presenter')
        self.cachedSize = None
        self.full_repaint = True
        self.link_map = None
        self.presenter_mode = is_presenter
        self.single_mode = is_single
        self.setMouseTracking(True)
        self.video_players = []
        self.slide_position = None
    
        # Place the selected view fullscreen on the selected monitor
        self.showFullScreen()
        self.setGeometry( desktop_info.screenGeometry(target_desktop) )
    
    
    def setup(self):
        "Called at each repaint: returns the screen size and reconfigure if it changed (which should not happen after startup)"
        size = self.size()
        if size == self.cachedSize:
            return size.width(),size.height()
        
        self.cachedSize = size
        border = 2
        width = size.width() - 2*border
        height = size.height() - 2*border
        
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
        r_overview = (border,border, width,height, onx, ony, 10)
        
        # presenter mode
        
        h_bottom = 3*height/20
        h_progress = h_bottom / 8
        icon_w = h_bottom - h_progress
        icon_top = height + h_progress/2 - h_bottom
        
        margin = h_progress
        icon_m = h_progress
        
        r_progress = (border,height-h_progress, width, h_progress)
        
        width -= h_progress
        height -= h_progress
        
        w_cur = 2*width/3
        h_cur= height - h_bottom
        h_next = 2*height/5
        r_cur = (border,border, w_cur, h_cur)
        x_side = border+w_cur+margin
        w_side = width - x_side - 2*h_progress
        h_side = h_cur/2 - h_progress
        r_over = (x_side, border, w_side, h_side)
        r_next = (x_side, border+h_side+2*h_progress, w_side, h_side)
        
        r_o_progress = (width-h_progress,border, h_progress, h_cur)
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
            "o_progress": r_o_progress,
            "overview": r_overview,
        }
        return width,height
    
    def keyPressEvent(self, e):
        self.app.handle_key(e)
    
    def mouseMoveEvent(self, e):
        l = self.app.has_moved(e, self.link_map)
    
    def refresh(self, full=True):
        if full:
            self.full_repaint = True
        self.update()
    
    def repaint(self):
        width,height = self. setup()
        self.slide_position = None
        
        qp = QtGui.QPainter()
        qp.begin(self)
        if self.app.overview_mode and (self.presenter_mode or self.single_mode):
            self.paint_overview(qp, width, height)
        elif self.presenter_mode or (self.single_mode and not self.app.clock_start):
            self.paint_presenter(qp, width, height)
        else:
            self.paint_slide(qp, width, height)
        
        if self.app.helping and (self.presenter_mode or self.single_mode):
            show_help(qp, width, height)
        
        # make sure that no video is left running in wrong cases
        if not self.slide_position:
            self.stop_videos()
        
        qp.end()
        
    
    def paint_slide(self, qp, width, height):
        if self.doc.color:
            qp.setBrush(self.doc.color)
            qp.drawRect(0, 0, width, height)
        else:
            # black background
            qp.setBrush(BG)
            qp.drawRect(0, 0, width, height)
            
            self.link_map = []
            info = self.doc.get_slide()
            place_image(qp, info, 0,0, width,height, self.link_map, LINK_N, view=self)
    
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
            place_image(qp, info, x,y,w,h, self.link_map, linkPaint, align=-1)
            
            # progressbar for the current overlay
            if info.overlay.count > 1:
                x,y,w,h = self.layout["o_progress"]
                show_progress(qp, x,y, w,h, info.o_n+1, info.overlay.count)
            
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
                place_image(qp, o_info, x,y,w,h, note=note, align=1)
                self.link_map.append( (x,y,x+w,y+h, o_info) )
            
            
            x,y,w,h = self.layout["next"]
            n_info = self.doc.get_next()
            if n_info:
                place_image(qp, n_info, x,y,w,h, align=1)
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
    
    def stop_videos(self):
        if not self.video_players:
            return False
        
        for movie in self.video_players:
            movie.stop()
        self.video_players = []
        return True
    
    def video(self, x,y,w,h, url, ef):
        if not self.slide_position:
            return
        
        media = get_media_source(url, ef)
        
        if not media:
            # TODO: some GUI feedback
            print("no video source could be created")
            return
        
        dx,dy, fx,fy = self.slide_position
        x = dx + x*fx
        y = dy + y*fy
        w *= fx
        h *= fy
        
        self.video_players.append( Movie(self, media, x,y, w,h) )


class Movie:
    def __init__(self, parent, media, x,y,w,h):
        self.player = Phonon.VideoPlayer( parent )
        self.player.setGeometry(x,y,w,h)
        self.player.show()
        self.player.load(media)
        self.player.play()
    
    def stop(self):
        if self.player:
            self.player.stop()
            self.player.hide()
            self.player.setParent(None)


def get_media_source(url=None, embeddedFile=None):
    "Turn an external link or n embded file into a playable media source"
    
    if url:
        try:
            return Phonon.MediaSource(url)
        except:
            print( "Failed to open video file ", url )
    
    if embeddedFile:
        try:
            videoData = embeddedFile.data()
            if COPY_EMBEDDED_VIDEO:
                # first copy the file to /tmp
                # do not autoremove the temp file: it happens too soon
                tmp = QtCore.QTemporaryFile()
                tmp.setAutoRemove(False)
                tmp.open()
                tmp.write( videoData )
                tmp.close()
                print( "playing embedded file from ", tmp.fileName() )
                return Phonon.MediaSource( tmp.fileName() )
            else:
                # play the embedded file directly: cleaner but not working
                buff = QtCore.QBuffer( videoData )
                #buff.open( QtCore.QIODevice.ReadOnly )
                return Phonon.MediaSource( buff )
        except:
            print( "Failed to open video from data" )
    return media


class Document:
    """The document wrapper:
        * load the file
        * provides a list of pages
        * remember the current and frozen pages
    """
    
    def __init__(self, filename):
        try:
            self.doc = popplerqt4.Poppler.Document.load(filename)
        except:
            print( "Error loading the file" )
            sys.exit()
        
        self.basedir = os.path.dirname(filename)
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
            if info.overlay.count == 1:
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
            if overlay < cur.overlay.count:
                cur = cur.overlay.pages[overlay]
            else:
                cur = cur.overlay.pages[-1]
            self.current = cur
            return True
        
        return False
    
    def freeze(self):
        if self.freezed is None:
            self.freezed = self.current
        else:
            self.freezed = None
    
    def next(self, skip_overlay=False):
        next = self.current.get_next(skip_overlay)
        if next:
            self.current = next
            return True
        
        return False
    
    def prev(self, skip_overlay=False):
        prev = self.current.get_prev(skip_overlay)
        if prev:
            self.current = prev
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
        return self.current.get_next_overlay()
    
    def get_page_info(self, p,o):
        pass


class OverlayInfo:
    def __init__(self,page):
        self.count = 0
        self.pages = []
        self.add_page(page)
    
    def add_page(self, page):
        page.o_n = self.count
        page.overlay = self
        self.count += 1
        self.pages.append( page )
    def get(self, n):
        if n<0 or n>=self.count:
            return None
        return self.pages[n]

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
        
        # build linked list as we visit new pages
        if not prev or prev.label != self.label:
            # adding a new logical page
            self.n = len(doc.layout)
            if prev :
                self.prev = prev.overlay.get(0)
                # adding self as next page for the previous overlay
                for p in prev.overlay.pages:
                    p.next = self
            else:
                self.prev = prev
            OverlayInfo(self)
            
        else:
            # Adding to the same overlay
            self.n = prev.n
            # update overlay count
            prev.overlay.add_page(self)
            self.prev = prev.prev
        
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
                    pass
                else:
                    # other types of links to support?
                    print( type(link) )
                    pass
            self.get_movies()
        
        return self.links
    
    def get_movies(self):
        movies = []
        for annot in self.page.annotations():
            if isinstance(annot, popplerqt4.Poppler.MovieAnnotation):
                # movie annotation to a separate file (as added by beamer)
                area = annot.boundary()
                x = area.x()
                y = area.y()
                w = area.width()
                h = area.height()
                url = str( annot.movie().url() )
                url = os.path.join(self.doc.basedir, url)
                url= os.path.abspath( url )
                if not url.startswith( self.doc.basedir ):
                    print("External movies only accepted in current or sub folders")
                else:
                    movies.append( (x,y,w,h, url,None) )
            elif isinstance(annot, popplerqt4.Poppler.FileAttachmentAnnotation):
                # Detect movies in file attachment annotations (inserted by movie15 in LaTeX)
                area = annot.boundary()
                x = area.x()
                y = area.y()
                w = area.width()
                h = area.height()
                annot.contents() # gives the MIME type: 'Media File (video/mp4)'
                # TODO: how to check if it is indeed a playable movie ?
                if True:
                    f = annot.embeddedFile() # gives the file itself
                    movies.append( (x,y,w,h, None,f) )
        
        return movies
    
    def get_next_overlay(self):
        return self.overlay.get(self.o_n+1)
        
    def get_prev_overlay(self):
        return self.overlay.get(self.o_n-1)
    
    def get_next(self, skip_overlay=False):
        if not skip_overlay:
            next = self.get_next_overlay()
            if next: return next
        return self.next
    
    def get_prev(self, skip_overlay=False):
        if not skip_overlay:
            prev = self.get_prev_overlay()
            if prev: return prev
        if self.o_n > 0:
            return self.overlay.get(0)
        
        return self.prev
    
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


COPY_EMBEDDED_VIDEO = True

# colors
HUE = 225           # Hue for all colors
HUE = 225           # Hue for all colors
# fancy HSV color setup: change the HUE to change the theme
RED = 0
BROWN = 40
GREEN = 120
BLUE = 240

HUE = BLUE
sL, vL =  20,200    # saturation and value for the light color
sM, vM = 100,200    # saturation and value for the intermediate color
sF, vF = 255,150    # saturation and value for the highlight
sS, vS = 250,200    # saturation and value for the selection

BLACK   = QtGui.QColor(0, 0, 0)
WHITE   = QtGui.QColor(255, 255, 255)

BG      = BLACK
TEXT    = WHITE
HELP_BG = QtGui.QColor(30, 30, 30, 220)
DIM     = QtGui.QColor(50, 50, 50, 100)
ICON    = QtGui.QColor.fromHsv(HUE, sL, vL)
COLD    = QtGui.QColor.fromHsv(HUE,sM,vM)
HG      = QtGui.QColor.fromHsv(HUE,sF,vF)
SEL     = QtGui.QColor.fromHsv(HUE,sS,vS)

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


