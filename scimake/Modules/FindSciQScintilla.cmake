# - FindSciQScintilla: Module to find include directories and
#   libraries for QScintilla.
#
# Module usage:
#   find_package(SciQScintilla ...)
#
# This module will define the following variables:
#  HAVE_QSCINTILLA, QSCINTILLA_FOUND = Whether libraries and includes are found
#  QScintilla_INCLUDE_DIRS       = Location of QScintilla includes
#  QScintilla_LIBRARY_DIRS       = Location of QScintilla libraries
#  QScintilla_LIBRARIES          = Required libraries

#################################################
#
# Find module for QScintilla includes and lib
#
# $Id: FindSciQScintilla.cmake 792 2015-04-17 14:07:44Z jrobcary $
#
# Copyright 2010-2015, Tech-X Corporation, Boulder, CO.
# See LICENSE file (EclipseLicense.txt) for conditions of use.
#
#
#################################################

SciFindPackage(
        PACKAGE QScintilla
        INSTALL_DIR QScintilla
        HEADERS qsciscintilla.h
        LIBRARIES qscintilla2
        INCLUDE_SUBDIRS "include/Qsci"
        )

if (QSCINTILLA_FOUND)
  message(STATUS "[FindQScintilla.cmake] - Found QScintilla")

  # This is a funny thing in QScintilla-
  # We want to have the actual path to the qscintilla installs
  # BUT the qscintilla headers all use "QSci/xx.h"
  # So we also need to next directory down
  if (DEBUG_CMAKE)
    message(STATUS "QScintilla_INCLUDE_DIRS is ${QScintilla_INCLUDE_DIRS}")
  endif ()
  set(QScintilla_INCLUDE_DIRS_TEMP ${QScintilla_INCLUDE_DIRS})
  foreach (qdir ${QScintilla_INCLUDE_DIRS_TEMP})
    get_filename_component(qdir_cdup "${qdir}/.." REALPATH)
    set(QScintilla_INCLUDE_DIRS ${QScintilla_INCLUDE_DIRS} ${qdir_cdup})
  endforeach ()

  if (DEBUG_CMAKE)
    message(STATUS "QScintilla_INCLUDE_DIRS is ${QScintilla_INCLUDE_DIRS}")
  endif ()

else ()
  message(STATUS "[FindQScintilla.cmake] - QScintilla not found, use -DQSCINTILLA_DIR to supply the installation directory.")
  if (SciQScintilla_FIND_REQUIRED)
    message(FATAL_ERROR "[FindQScintilla.cmake] - Failing.")
  endif ()
endif ()

