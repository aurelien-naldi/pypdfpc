import os, sys
import time
import popplerqt4
import gui


# label for automatic note detection
NOTE_LABEL = "0"


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
        for p in range(self.lastPage):
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
        
        # enable anti aliasing
        self.doc.setRenderHint(popplerqt4.Poppler.Document.TextAntialiasing)
        self.doc.setRenderHint(popplerqt4.Poppler.Document.Antialiasing)
    
    
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
        self.cached = {}
        
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
        self.videos = None
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
        
        return self.links
    
    def get_videos(self):
        if self.videos is None:
            self.videos = []
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
                        print("External videos only accepted in current or sub folders")
                    else:
                        media = gui.get_media_source(url,None)
                        self.videos.append( (x,y,w,h, media) )
                elif isinstance(annot, popplerqt4.Poppler.FileAttachmentAnnotation):
                    # Detect movies in file attachment annotations (inserted by movie15 in LaTeX)
                    area = annot.boundary()
                    x = area.x()
                    y = area.y()
                    w = area.width()
                    h = area.height()
                    annot.contents() # gives the MIME type: 'Media File (video/mp4)'
                    # TODO: how to check if it is indeed a playable video ?
                    if True:
                        f = annot.embeddedFile() # gives the file itself
                        media = gui.get_media_source(None,f)
                        self.videos.append( (x,y,w,h, media) )
        
        return self.videos
    
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
        if width > 400:
            return self.render_image(width, height, note)
        size = (width,height)
        if size not in self.cached:
            self.cached[size] = self.render_image(width, height, note)
        return self.cached[size]

    def render_image(self, width, height, note=False):
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

