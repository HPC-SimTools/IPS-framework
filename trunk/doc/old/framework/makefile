#!/bin/sh

#pdflatex fmwk.tex
#bibtex fmwk
#pdflatex fmwk.tex
#pdflatex fmwk.tex

pdf:
	pdflatex fmwk.tex; bibtex fmwk; pdflatex fmwk.tex
# 	pdflatex fmwk.tex; bibtex fmwk; pdflatex fmwk.tex; pdflatex fmwk.tex

ps:
	latex fmwk.tex; bibtex fmwk; latex fmwk.tex; dvips -o fmwk.ps fmwk.dvi
#	latex fmwk.tex; bibtex fmwk; latex fmwk.tex; latex fmwk.tex; dvips -o fmwk.ps fmwk.dvi


clean:
	rm -f *~ *.log *.ps fmwk.pdf fmwk.bbl fmwk.blg *.dvi *.aux
