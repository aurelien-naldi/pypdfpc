PDF presenter tool
==================

Fast and easy presentation tool for PDF files.
It aims to make my presentations slightly more confortable,
but also to teach me about poppler and Qt.


Features
--------

The screenshots (taken with pdfpc's demo presentation) give a good first taste.

Main features:
* Presenter screen with current and next slide, timer and progress bar
* Play (some) videos inline
* Note slides in the presenter view
* Overview mode: view and select slides
* Detect beamer's overlays (successive pages with the same label):
  don't count them in the global progress, fast forward and overview
* Freeze the main screen
* Hide the main screen (black or white)
* Escape will unfreeze and unhide before exiting
* No installation, no setup, no command-line option:
* show help on screen and on the command line (if no file is given)


Two screens mode:
* presenter console on the first screen
* slide view on the second screen
* they can be switched
* overview visible on the presenter screen only


Single screen mode:
* show the slide view by default
* can switch between slide and presenter console
* always show the presenter console when paused
* freezing is disabled
* overview always visible


Supported notes types:
* Beamer "show notes on second screen" mode is supported if the file name ends with
  ".right", ".left", ".top", or ".bottom" (before the .pdf extension).
  Note that with this option, beamer tends to mess page number, which break
  the overlay support.
* Beamer's "show notes" mode is supported if the note pages are given
  page number "0". See the example tex to set this up.
* LibreOffice can export note pages at the end of the document, they wil be used
  if the file name ends with ".end.pdf". For good results, you are encouraged to
  adapt the notes master page.


Playing movies:

Video support exists but is limited.
The objects should be properly placed on the main slide,
changing slide, pausing, going to the overview will stop the video.
Pause, click to play and overview indicators are not yet implemented.


Note that several methods exist for video objects, and generating a
compatible PDF file can be tricky. As far as I can tell,
this tool should support the two standard methods thanks to phonon
and the poppler backend.
* The old and simple "Movie Annotation", which define a link to an external file.
  This is beamer's encouraged method (using the multimedia package).
  These videos are played inline if the target file is in the same folder as the
  PDF file, or in a subfolder (other links are rejected out of paranoia).
* The standard Screen Annotation method provides video data as file attachments.
  This is generated by the movie15 LaTeX package.
  Unfortunately Phonon fails to load attachments directly, the data is thus copied
  to a temporary file before loading: slower and leaves some dust in /tmp.
  Play settings are not supported yet.


Non-standard methods relying on javascript or flash are not on the radar:
they are too complex and bring more security risks than real advantages.
LaTeX documents using the media9 package generate such files:
despite claiming to replace movie15, this package should be avoided.

If you want to insert videos into your beamer slides, I suggest the multimedia package:

  \usepackage{multimedia}
  
  \movie[width=3cm,height=2cm]{VIDEO}{vid/mov_bbb.mp4}



Some missing-but-would-be-nice-to-have features:

* text notes based on PDF annotations
* countdown mode for the timer
* transitions (based on PDF annotation)



Depends
-------

It is tested with python 2.7, and probably ready for python3.

It requires the following python bindings:
* PyQt4
* python-poppler-qt4


Fedora:
    dnf install PyQt4 python-poppler-qt4


Debian/Ubuntu:
    apt-get install python-qt4 python-poppler-qt4 python-qt4-phonon



Related tools
-------------

Here are a few other presenter tools for PDF documents:


* https://code.google.com/p/pdf-presenter/
* http://code.100allora.it/pdfcube/
* http://impressive.sourceforge.net/
  - fancy transitions
  - highlight cursor or selection
* http://davvil.github.io/pdfpc/
  - main inspiration: supports overlays, overview, freeze
  - has video support in git (not released and apparently it needs porting to newer vala)
* http://sourceforge.net/projects/qpdfpresenter/
  - video support


