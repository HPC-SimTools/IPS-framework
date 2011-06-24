# tailored to generate both original paper
# and a flat version and (if configured) the
# old style version all from the same tex sources.
# uses a local copy of flatex to flatten and do bbl silliness.


DVIPS = dvips
DVIPDF = dvipdfm
BIBTEX = bibtex
PDFLATEX = pdflatex


FILENAME=user_guide

SOURCES = \
$(FILENAME).bib \
$(shell ls *.tex ) \
$(shell ls figures/*ps)

all: clean ps 

clean:
	rm -f table*.eps *.dvi *.ps *.ps.Z *.jps *.log *.blg *.aux *.bbl *pdf 

.SUFFIXES: .bib .tex .dvi .fig .ps .pdf

pdf: $(FILENAME).pdf

$(FILENAME).pdf: $(SOURCES) 
	pdflatex $(FILENAME)
	- bibtex $(FILENAME)
	pdflatex $(FILENAME)
	pdflatex $(FILENAME)

ps:$(FILENAME).ps

$(FILENAME).ps: $(SOURCES)
	latex $(FILENAME)
	- bibtex $(FILENAME)
	latex $(FILENAME)
	latex $(FILENAME)
	dvips -t letter -o $(FILENAME).ps $(FILENAME).dvi
	ps2pdf $(FILENAME).ps 

x:
	@echo $(SOURCES)
   
texclean:
	rm -f *.dvi *.aux *.blg *.log

.fig.ps:
	fig2ps < $*.fig > $*.ps

.dvi.ps:
	$(DVIPS) -t letter -o $*.ps $*.dvi 

.dvi.pdf:
	$(DVIPDF) -o  $*.pdf $*.dvi
