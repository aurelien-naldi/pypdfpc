import os, sys
import math
import time
import traceback
from PyQt4 import QtGui, QtCore
from PyQt4.phonon import Phonon


COPY_EMBEDDED_VIDEO = True

# fancy HSV color setup: change the HUE to change the theme
RED,BROWN,GREEN,BLUE = 0,40,120,240
HUE = BLUE
HUE2 = GREEN

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
SEL2     = QtGui.QColor.fromHsv(HUE2,sS,vS)

LINK = QtGui.QColor(200, 50, 50, 50)


FROZEN = "F"


class StatusBar(QtGui.QWidget):
    "The bottom bar of the presenter console: shows a timer and status icons"
    def __init__(self, app, view):
        self.app = app
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
        show_progress(qp, 0, h-margin, w,margin, self.app.get_current().n+1, len(self.app.doc.layout))
        
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
        self.info = None
        self.image = None
        self.baits = []
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
        
        # clear old links
        if not self.image or self.app.color:
            for bait in self.baits:
                bait.clear()
            self.baits = []
        
        
        qp = QtGui.QPainter()
        qp.begin(self)
        
        if self.app.color:
            qp.setBrush(self.app.color)
            qp.drawRect(0, 0, width, height)
        elif self.info:
            if not self.image:
                self.image = self.info.get_image(width,height)
                ix,iy,iw,ih = paint_image(qp, self.image, 0,0,width,height)
            
                # add links
                for l in self.info.get_links():
                    ax = ix + iw * l.x
                    ay = iy + ih * l.y
                    aw = iw * l.w
                    ah = ih * l.h
                    bait = LinkBox(self, l.page, ax,ay,aw,ah)
                    self.baits.append( bait )
                
                # add videos
                for vx,vy,vw,vh,media in self.info.get_videos():
                    if not media:
                        continue
                    
                    ax = ix + iw * vx
                    ay = iy + ih * vy
                    aw = iw * vw
                    ah = ih * vh
                    bait = VideoBox(self, ax,ay,aw,ah, media)
                    self.baits.append(bait)
            else:
                paint_image(qp, self.image, 0,0,width,height)
            
        qp.end()
    
    def video(self):
        for bait in self.baits:
            if isinstance(bait,VideoBox):
                bait.activate()
    
    def stop(self):
        found = False
        for bait in self.baits:
            if isinstance(bait,VideoBox):
                found = found or bait.clear()
        return found


class ClickBait(QtGui.QWidget):
    "Base class for links and videos: take up the reserved space and detect clicks"
    
    def __init__(self, view, x,y,w,h):
        super(ClickBait, self).__init__(view)
        self.setCursor( QtGui.QCursor(QtCore.Qt.PointingHandCursor) )
        self.setGeometry(x,y,w,h)
        self.show()
    
    def activate(self):
        pass
    
    def clear(self):
        self.hide()
        self.setParent(None)
    
    def mouseReleaseEvent(self, evt):
        self.activate()


class LinkBox(ClickBait):
    "PDF links: jump to another page on the same document"
    def __init__(self, view, target, x,y,w,h):
        super(LinkBox, self).__init__(view, x,y, w,h)
        self.app = view.app
        self.target = target
    
    def activate(self):
        self.app.set_current(self.target)


class SideBar(QtGui.QWidget):
    def __init__(self, app, view):
        self.app = app
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
        self.doc = app.doc
        # pick settings for the overview
        self.n = n = len(self.doc.layout)
        onx = 3
        ony = 2
        while n > onx*ony:
            if ony < onx:
                ony += 1
            else:
                onx += 1
            if onx > 6:
                break
        self.onx = onx
        self.ony = ony
        self.nthumbs = onx * ony
        self.npages = math.ceil(n / self.nthumbs)

        self.thumbs = []
        self.selected = None
        self.start = 0
        
        super(Overview, self).__init__(view)
    
    def clear(self):
        for t in self.thumbs:
            t.clear()
    
    def move_selection(self, m):
        if self.selected is None:
            return
        
        newsel = self.selected + m
        if newsel < 0:
            newsel = 0
        elif self.selected >= self.n:
            new = self.n-1
        
        if newsel != self.selected:
            self.thumbs[self.selected].select(False)
            self.thumbs[newsel].select()
            self.selected = newsel
    
    def next(self):
        self.move_selection(1)
    
    def prev(self):
        self.move_selection(-1)
    
    def refresh(self):
        # TODO: multipage overview
        #  * shift starting point
        #  * show page indicators
        
        self.clear()
        
        size = self.size()
        width =  size.width()
        height = size.height()
        m = margin = 10
        
        x = y = margin/2
        w = width - margin
        h = height - margin
        
        
        n = len(self.doc.layout)
        
        dx = w / self.onx
        mw = dx-m
        
        dy = h/self.ony
        mh = dy-m
        
        mm = m/2
        cury = y+mm
        self.link_map = []
        current = self.app.get_current().overlay.pages[0]
        current_o = self.app.get_current_overview().overlay.pages[0]
        # find the starting page
        self.start = 0
        nthumbs = self.nthumbs - 2
        if n > self.nthumbs and current_o.n > nthumbs:
            skipped = int(math.floor( (current_o.n - 1) / nthumbs ))
            self.start = nthumbs * skipped + 1
        i = self.start
        for line in range(self.ony):
            curx = x+mm
            for col in range(self.onx):
                if i >= n:
                    break
                if self.start > 0 and line == 0 and col == 0:
                    # Link to the previous page
                    info = self.doc.layout[i-1]
                    box = PrevNextBox(self, info, curx,cury,mw,mh, True)
                    self.thumbs.append(box)
                elif line == self.ony-1 and col == self.onx-1 and i < n:
                    # Link to the next page
                    info = self.doc.layout[i]
                    box = PrevNextBox(self, info, curx,cury,mw,mh, False)
                    self.thumbs.append(box)
                else:
                    info = self.doc.layout[i]
                    is_current = info==current
                    is_selected = info==current_o
                    box = ThumbBox(self, info, is_current, is_selected, curx,cury,mw,mh)
                    self.thumbs.append(box)
                    i += 1
                curx += dx
            cury += dy

class ThumbBox(ClickBait):
    "Thumbnail in the overview"
    
    def __init__(self, view, target, is_current, is_selected, x,y,w,h):
        super(ThumbBox, self).__init__(view, x,y, w,h)
        self.app = view.app
        self.target = target
        self.is_current = is_current
        self.is_selected = is_selected
        self.image = None
    
    def select(self, s=True):
        self.is_selected = s
        self.update()
    
    def resizeEvent(self, evt):
        self.image = None
    
    def activate(self):
        self.app.set_current_overview(self.target, True)

    def paintEvent(self, evt):
        size = self.size()
        width =  size.width()
        height = size.height()

        if not self.image:
            self.image = self.target.get_image(width-10, height-10)

        qp = QtGui.QPainter()
        qp.begin(self)

        if self.is_selected:
            qp.setBrush(SEL2)
        elif self.is_current:
            qp.setBrush(SEL)
        else:
            qp.setBrush(ICON)

        qp.drawRect(0,0, width,height)
        paint_image(qp, self.image, 0,0,width,height)
        qp.end()

class PrevNextBox(ClickBait):
    "Prev/Next page in the overview"

    def __init__(self, view, target, x,y,w,h, is_prev):
        super(PrevNextBox, self).__init__(view, x,y, w,h)
        self.view = view
        self.target = target
        self.is_selected = False
        self.is_prev = is_prev

    def select(self, s=True):
        self.is_selected = s
        self.update()

    def activate(self):
        self.view.app.set_current_overview(self.target)

    def paintEvent(self, evt):
        size = self.size()
        width =  size.width()
        height = size.height()

        qp = QtGui.QPainter()
        qp.begin(self)

        qp.setBrush(WHITE)

        # TODO: draw some arrow thingie
        qp.drawRect(10, height/2 - 5, width - 20, 10)
        if self.is_prev:
            px  = int(2*width/3)
            pxx = width - 10
        else:
            px = int(width/3)
            pxx = width + 10
        y_up = int(height/3)
        y_down = int(2*height/3)
        y_mid = int(height/2)
        arrow = QtGui.QPolygon( (px,y_up, pxx,y_mid, px,y_down) )
        qp.drawPolygon( arrow )
        qp.end()


class HelpBox(QtGui.QWidget):
    def __init__(self, app, view):
        self.app = app
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
        self.link_map = None
        self.presenter_mode = is_presenter
        self.single_mode = is_single

        super(View, self).__init__()
        self.setStyleSheet("background-color:black;")
        self.setWindowTitle('Simple PDF presenter')
        self.setMouseTracking(True)
        self.video_players = []
        self.slide_position = None
        
        # add child widgets
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
        "reconfigure the layout upon resize (which should not happen after startup)"
        size = self.size()
        width = size.width()
        height = size.height()
        
        # evaluate space for the slide, status, and side bars
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
            self.overview.refresh()
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
        if self.app.overview_mode and (self.presenter_mode or self.single_mode):
            self.overview.refresh()
        elif self.presenter_mode:
            self.slideview.set_slide(self.app.get_current())
        else:
            self.slideview.set_slide(self.app.get_slide())
        self.update()
    
    
    def mouseReleaseEvent(self, evt):
        self.app.click_map(evt, self.link_map)
    
    def stop_videos(self):
        return self.slideview.stop()
    
    def video(self):
        self.slideview.video()
    


class VideoBox(ClickBait):
    "Placeholder widget for inline videos"
    def __init__(self, view, x,y,w,h, media):
        super(VideoBox, self).__init__(view,x,y,w,h)
        self.media = media
        self.player = None
    
    def activate(self):
        if not self.player:
            w = self.size().width()
            h = self.size().height()
            self.player = Phonon.VideoPlayer( self )
            self.player.setGeometry(0,0,w,h)
            self.player.show()
            self.player.load(self.media)
            self.player.play()
        else:
            self.clear()
    
    def clear(self):
        if self.player:
            self.player.stop()
            self.player.hide()
            self.player.setParent(None)
            self.player = None


def get_media_source(url=None, embeddedFile=None):
    "Turn an external link or embded file into a playable media source"
    
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



def place_image(qpainter, info, x,y,w,h, note=False, align=0):
    "Paint a page info properly aligned in the selected area"
    if info:
        image = info.get_image(w,h, note)
        paint_image(qpainter, image, x,y,w,h, align)

def paint_image(qpainter, image, x,y,w,h, align=0):
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
    
    return (x,y,iw,ih)


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
            for i in range(total):
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


