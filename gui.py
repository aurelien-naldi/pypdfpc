from __future__ import print_function, division

import os, sys
import time
from PyQt4 import QtGui, QtCore
from PyQt4.phonon import Phonon


COPY_EMBEDDED_VIDEO = True

# fancy HSV color setup: change the HUE to change the theme
RED,BROWN,GREEN,BLUE = 0,40,120,240
HUE = BLUE

sL, vL =  20,200    # saturation and value for the light color
sM, vM = 100,200    # saturation and value for the intermediate color
sF, vF = 255,150    # saturation and value for the highlight
sS, vS = 250,200    # saturation and value for the selection

BLACK   = QtGui.QColor(0, 0, 0)
WHITE   = QtGui.QColor(255, 255, 255)

BG      = BLACK
TEXT    = WHITE
HELP_BG = QtGui.QColor(0, 0, 0, 200)
HELP_BG = BLACK
DIM     = QtGui.QColor(50, 50, 50, 100)
ICON    = QtGui.QColor.fromHsv(HUE, sL, vL)
COLD    = QtGui.QColor.fromHsv(HUE,sM,vM)
HG      = QtGui.QColor.fromHsv(HUE,sF,vF)
SEL     = QtGui.QColor.fromHsv(HUE,sS,vS)

LINK = QtGui.QColor(200, 50, 50, 50)


FROZEN = "F"


class StatusBar(QtGui.QWidget):
    def __init__(self, app, view):
        self.app = app
        self.view = view
        self.doc = app.doc
        super(StatusBar, self).__init__(view)
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self.refresh)
        self._timer.start(500)
        self.h_icon = None
    
    def refresh(self):
        self.update()
    
    def paintEvent(self, e):
        size = self.size()
        width = w = size.width()
        height = h = size.height()
        margin = h/8
        h_icon = 6*h/8
        timer_w = 4*h_icon
        if h_icon != self.h_icon:
            self.h_icon = h_icon
            # detect DPI to select the proper font size
            font_scale = QtGui.QDesktopWidget().physicalDpiX() / 96
            font_size = h_icon - 2*margin
            self.font = QtGui.QFont('Sans', font_size/font_scale)
        
        qp = QtGui.QPainter()
        qp.begin(self)
        
        qp.setBrush(HELP_BG)
        qp.setPen(HELP_BG)
        qp.drawRect(0,0,w,h)
        show_progress(qp, 0, h-margin, w,margin, self.app.get_current().n+1, len(self.doc.layout))
        
        qp.setPen(TEXT)
        qp.setFont(self.font)
        seconds,paused = self.app.get_clock()
        minutes = seconds / 60
        seconds %= 60
        hours = minutes / 60
        minutes %= 60
        timetext = "%02d:%02d:%02d" % (hours,minutes,seconds)
        qp.drawText(0,0,w,h, QtCore.Qt.AlignCenter, timetext)
        

        x = margin - height
        y = margin/2
        m = h_icon/8
        w = h_icon
        
        qp.setPen(ICON)
        if self.app.color:
            x += height
            qp.setBrush(ICON)
            qp.drawRect(x,y,w,w)
            qp.setBrush(self.app.color)
            qp.drawRect(x+m,y+m,w-2*m,w-2*m)
        
        if self.app.freezed:
            x += height
            qp.setBrush(ICON)
            qp.drawEllipse(x,y,w,h)
            qp.setPen(COLD)
            qp.drawText(x+m,y+m,w-2*m,h-2*m, QtCore.Qt.AlignCenter, FROZEN)
        
        if paused:
            x = width - height
            qp.setBrush(ICON)
            qp.drawEllipse(x,y,w,w)
            qp.setBrush(BG)
            dx = w/20
            bw = w/4 - dx
            bh = 3*w/5
            qp.drawRect(x+w/4, y+w/5, bw, bh)
            qp.drawRect(x+w/2+dx, y+w/5, bw, bh)
        
        qp.end()

class SlideView(QtGui.QWidget):
    def __init__(self, app, view):
        self.app = app
        self.view = view
        self.doc = app.doc
        self.info = None
        self.image = None
        super(SlideView, self).__init__(view)
    
    def set_slide(self, info):
        if self.info != info:
            self.info = info
            self.image = None
        
        if not self.image:
            self.update()
        
    def resizeEvent(self, evt):
        self.image = None
    
    def paintEvent(self, e):
        size = self.size()
        width =  size.width()
        height = size.height()
        
        qp = QtGui.QPainter()
        qp.begin(self)
        
        
        if self.app.color:
            qp.setBrush(self.app.color)
            qp.drawRect(0, 0, width, height)
        else:
            self.link_map = []
            if self.info and not self.image:
                self.image = self.info.get_image(width,height)
            paint_image(qp, self.image, 0,0,width,height)
        qp.end()


class SideBar(QtGui.QWidget):
    def __init__(self, app, view):
        self.app = app
        self.view = view
        self.doc = app.doc
        super(SideBar, self).__init__(view)
    
    def refresh(self):
        self.update()
    
    def paintEvent(self, e):
        size = self.size()
        width =  size.width()
        height = size.height()
        margin = width/20
        
        x = margin/2
        y = x
        w = width - 2*margin
        h = (height-margin)/2
        
        info = self.app.get_current()
        
        
        qp = QtGui.QPainter()
        qp.begin(self)
        
        # notes / overlay
        if info.has_note:
            note=True
            o_info = info
        else:
            o_info = self.app.get_next_overlay()
            note=False
        if o_info:
            place_image(qp, o_info, x,0,w,h, note=note, align=1)
        
        # next
        y += h
        n_info = self.app.get_next()
        if n_info:
            place_image(qp, n_info, x,h+margin,w,h, align=1)
        
        
        # progressbar for the current overlay
        if info.overlay.count > 1:
            x = width-margin
            show_progress(qp, width-margin,0, margin,height, info.o_n+1, info.overlay.count)
        
        qp.end()


class Overview(QtGui.QWidget):
    def __init__(self, app, view):
        self.app = app
        self.view = view
        self.doc = app.doc
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
        self.onx = onx
        self.ony = ony
        
        super(Overview, self).__init__(view)
    
    def paintEvent(self, e):
        # TODO: multipage overview
        #  * shift starting point
        #  * show page indicators
        
        size = self.size()
        width =  size.width()
        height = size.height()
        m = margin = width/20
        
        x = y = margin/2
        w = width - margin
        h = height - margin
        
        qp = QtGui.QPainter()
        qp.begin(self)
        
        qp.setBrush(BG)
        qp.drawRect(x,y, w,h)
        
        n = len(self.doc.layout)
        start = 0
        
        qp.setBrush(BG)
        qp.drawRect(0, 0, width, height)
        
        dx = w / self.onx
        mw = dx-m
        
        dy = h/self.ony
        mh = dy-m
        
        mm = m/2
        cury = y+mm
        i = start
        self.link_map = []
        for line in xrange(self.ony):
            curx = x+mm
            for col in xrange(self.onx):
                
                if i >= n:
                    break
                info = self.doc.layout[i]
                place_image(qp, info, curx,cury,mw,mh)
                self.link_map.append( (curx,cury,curx+mw,cury+mh, info) )
                i += 1
                curx += dx
            cury += dy
        
        qp.end()

class HelpBox(QtGui.QWidget):
    def __init__(self, app, view):
        self.app = app
        self.view = view
        self.doc = app.doc
        super(HelpBox, self).__init__(view)
    
    def paintEvent(self, e):
        size = self.size()
        width =  size.width()
        height = size.height()
        margin = min(width,height) / 20
        
        help, n,l = self.app.get_help()
        
        qp = QtGui.QPainter()
        qp.begin(self)
        
        qp.setBrush(HELP_BG)
        qp.setPen(WHITE)
        qp.drawRect(0,0, width,height)
        
        # pick font size
        dpi = QtGui.QDesktopWidget().physicalDpiX()
        font_scale = dpi / 96
        font_size = min(width/(l+4), height/(n+8)) / font_scale
        help_font = QtGui.QFont('Mono', font_size)
        
        qp.setFont(help_font)
        qp.drawText(margin,margin,width-2*margin,height-2*margin,
             QtCore.Qt.AlignLeft, help)
        
        qp.end()

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
        self.app = app
        self.doc = app.doc
        self.cachedSize = None
        self.link_map = None
        self.presenter_mode = is_presenter
        self.single_mode = is_single

        super(View, self).__init__()
        self.setWindowTitle('Simple PDF presenter')
        self.setMouseTracking(True)
        self.video_players = []
        self.slide_position = None
        
        self.status = StatusBar(self.app, self)
        self.sidebar = SideBar(self.app, self)
        self.overview = Overview(self.app, self)
        self.slideview = SlideView(self.app, self)
        self.helpbox = HelpBox(self.app, self)
        
        
        # Place the selected view fullscreen on the selected monitor
        geometry = desktop_info.screenGeometry(target_desktop)
        self.setGeometry( geometry )
        self.showFullScreen()
        self.config_view()
        
    def resizeEvent(self, evt=None):
        self.setup()
    
    def setup(self):
        "Called at each repaint: returns the screen size and reconfigure if it changed (which should not happen after startup)"
        size = self.size()
        if size == self.cachedSize:
            return size.width(),size.height()
        
        self.cachedSize = size
        width = size.width()
        height = size.height()

        border = 2
        
        
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
        margin = h_bottom / 8
        
        w_cur = 2*width/3
        h_cur = height - h_bottom
        x_side = w_cur + margin
        w_side = width - x_side
        self.width = width
        self.height = height
        self.w_cur = w_cur
        self.h_cur = h_cur
        
        self.status.resize(width, h_bottom)
        self.status.move(0, height-h_bottom)
        self.sidebar.resize(w_side, h_cur)
        self.sidebar.move(x_side, 0)
        self.overview.resize(width,height)
        self.overview.move(0,0)
        self.helpbox.resize(width,height)
        self.helpbox.move(0,0)
        
        width -= margin
        h_next = 2*height/5
        
        r_cur = (border,border, w_cur, h_cur)
        h_side = h_cur/2 - margin
        r_over = (x_side, border, w_side, h_side)
        r_next = (x_side, border+h_side+2*margin, w_side, h_side)
        
        r_o_progress = (width-margin,border, margin, h_cur)
        
        
        self.layout = {
            "cur": r_cur,
            "over": r_over,
            "next": r_next,
            "o_progress": r_o_progress,
            "overview": r_overview,
        }
        return width,height
    
    def switch_mode(self):
        self.presenter_mode = not self.presenter_mode
        self.config_view()
    
    def config_view(self):
        if self.app.helping:
            self.slideview.hide()
            self.status.hide()
            self.sidebar.hide()
            self.overview.hide()
            self.helpbox.show()
        else:
            self.helpbox.hide()
        
        if self.app.overview_mode and (self.presenter_mode or self.single_mode):
            self.slideview.hide()
            self.status.hide()
            self.sidebar.hide()
            self.overview.show()
        elif self.presenter_mode:
            self.slideview.resize(self.w_cur, self.h_cur)
            self.overview.hide()
            self.slideview.show()
            self.status.show()
            self.sidebar.show()
        else:
            self.slideview.resize(self.width, self.height)
            self.overview.hide()
            self.status.hide()
            self.sidebar.hide()
            self.slideview.show()
        
        self.refresh()
    
    def keyPressEvent(self, e):
        self.app.handle_key(e)
    
    def mouseMoveEvent(self, e):
        l = self.app.has_moved(e, self.link_map)
    
    def refresh(self):
        self.update()
    
    def paintEvent(self, e):
        width,height = self. setup()
        self.slide_position = None
        
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setBrush(BG)
        qp.setPen(BG)
        qp.drawRect(0,0,width,height)
        
        
        if False and  self.app.overview_mode and (self.presenter_mode or self.single_mode):
            self.paint_overview(qp, width, height)
        elif self.presenter_mode:
            self.slideview.set_slide(self.app.get_current())
#            self.paint_presenter(qp, width, height)
        else:
            self.slideview.set_slide(self.app.get_slide())
        
        # make sure that no video is left running in wrong cases
        if not self.slide_position:
            self.stop_videos()
        
        qp.end()
        
    
    def paint_presenter(self, qp, width, height):
        # partial repaints are not yet working: widget is painted in grey first
        self.sidebar.show()
        self.status.show()
        self.link_map = []
        # background
        qp.setBrush(BG)
        qp.drawRect(0, 0, width, height)
        
        x,y,w,h = self.layout["cur"]
        info = self.app.get_current()
        place_image(qp, info, x,y,w,h, self.link_map, align=-1)
        
    
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



def place_image(qpainter, info, x,y,w,h, links=None, note=False, align=0, view=None):
    "Paint a page info properly aligned in the selected area"
    if info:
        image = info.get_image(w,h, note)
        paint_image(qpainter, image, x,y,w,h, links, align, view)

def paint_image(qpainter, image, x,y,w,h, links=None, align=0, view=None):
    if not image:
        return
    
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
    
    # TODO: rework link handling
    return
    
    for l in info.get_links():
        ax = x + iw * l.x
        ay = y + ih * l.y
        aw = iw * l.w
        ah = ih * l.h
        links.append( (ax,ay,ax+aw,ay+ah, l.page) )


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


