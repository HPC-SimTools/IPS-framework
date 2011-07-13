######################################################################
#
# CMakeLists.txt for docs
#
# $Id: CMakeLists.txt 1138 2011-01-28 00:25:57Z swsides $
#
######################################################################

#
# Useful variables
#
set (SRCDIR ${CMAKE_SOURCE_DIR}/doc)
set (BLDDIR ${CMAKE_BINARY_DIR}/doc)
set (SPHINXOPTS -D mathjax_path=${MATHJAXJS} -d ${BLDDIR}/doctrees ${SPHINX_OPTS} )
set (SPHINXRUN ${SPHINX_EXECUTABLE} ${SPHINXOPTS})

if(${ENABLE_WEBDOCS})
  message(STATUS "enable webdocs is on")
  set (INSTALLDIR   ${CMAKE_INSTALL_PREFIX})
else()
  message(STATUS "enable webdocs is off")
  set (INSTALLDIR   ${CMAKE_INSTALL_PREFIX}/docs)
endif()

#
# Installation of target: just do the whole directory
# 
install(DIRECTORY ${CMAKE_BINARY_DIR}/doc/
	DESTINATION ${INSTALLDIR}
  OPTIONAL
  COMPONENT docs
	PATTERN  "Makefile" EXCLUDE
	PATTERN  "cmake_install.cmake" EXCLUDE
	PATTERN  "CMakeFiles" EXCLUDE
	PATTERN  "Makefile.sphinx" EXCLUDE
	PATTERN  "conf.py" EXCLUDE
	PATTERN  ".svn" EXCLUDE)

##  Now invoke sphinx-build.
##   Sphinx-build outputs directly so we can output anywhere.  Because the pdf builds
##    generate a lot of extrenous stuff however, it is generally easier to output to the build
##    directory and then use CMakes install mechanism to handle the installs.

#  Output into build directory
add_custom_target(docs)

set (HTML_OUTPUT ${BLDDIR}/html/index.html)
add_custom_command(
   OUTPUT ${HTML_OUTPUT}
   COMMAND ${SPHINXRUN} -b html ${SRCDIR} ${BLDDIR}/html
)
add_custom_target(docs-html DEPENDS ${HTML_OUTPUT})

set (SINGLEHTML_OUTPUT ${BLDDIR}/singlehtml/index.html)
add_custom_command(
   OUTPUT ${SINGLEHTML_OUTPUT}
   COMMAND ${SPHINXRUN} -b singlehtml ${SRCDIR} ${BLDDIR}/singlehtml)
add_custom_target(docs-singlehtml DEPENDS ${SINGLEHTML_OUTPUT})

set (PDF_OUTPUT ${BLDDIR}/pdf/SphinxExample.pdf)
add_custom_command(
   OUTPUT ${PDF_OUTPUT}
   COMMAND ${SPHINXRUN} -b latex ${SRCDIR} ${BLDDIR}/pdf && make -C ${BLDDIR}/pdf all-pdf)
add_custom_target(docs-pdf DEPENDS ${PDF_OUTPUT})


set (MAN_OUTPUT ${BLDDIR}/man/index.man)
add_custom_command(
   OUTPUT ${MAN_OUTPUT}
   COMMAND ${SPHINXRUN} -b man ${SRCDIR} ${BLDDIR}/man)
add_custom_target(docs-man DEPENDS ${MAN_OUTPUT})

add_dependencies(docs docs-html docs-pdf docs-man)
