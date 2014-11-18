PDF presenter tool
==================

As I use PDF files for presentations, I've been looking for some kind of
presenter console for PDF files. Many such tools exist, but they are either
too fancy or too limited.

pdfpc is nearly perfect, but while I can compile the last release, 
the current git master does not seem to work with newer vala versions.

As I wanted to experiment with PyQt, I tried to reproduce the features I want
in this simple tool.
It started as an experiment, but it seems to work well enough for me: it does most
of what I wanted from pdfpc within less than 1k lines of python, thanks to the fantastic
poppler bindings. It also seems relatively fast with the (simple) presentations I tested.



Depends
-------

* python 2.7
* PyQt4
* python-poppler-qt4


How to use it?
--------------

No installation is needed.
Run the tool without arguments and it will print all shortcuts and actions.
Give it a PDF file as argument to start a presentation with it.

Current functions and shortcuts:

* next       Right Space      Go to the next slide or overlay
* prev       Left Backspace   Go to the previous slide or overlay
* forward    Down PgDown      Go to the next slide (skip overlays)
* backward   Up PgUp          Go to the previous slide (skip overlays)
* switch     S                Switch slide/presenter screens
* pause      P                Pause or unpause the timer
* freeze     F                Freeze the main slide (avoid disruption as you browse around)
* black      B                Turn the main display black
* white      W                Turn the main display white
* start      Home             Jump to the first slide
* reset      R                Jump to the first slide and reset the clock
* overview   Tab O            Show a grid of slides for quick visual selection
* escape     Esc Q            Leave modes (overview...), pause, quit the application



