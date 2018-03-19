# - FindSciGtest: Module to find include directories and
#   libraries for Gtest.
#
# Module usage:
#   find_package(SciGtest ...)
#
# This module will define the following variables:
#  HAVE_GTEST, GTEST_FOUND = Whether libraries and includes are found
#  Gtest_INCLUDE_DIRS       = Location of Gtest includes
#  Gtest_LIBRARY_DIRS       = Location of Gtest libraries
#  Gtest_LIBRARIES          = Required libraries

######################################################################
#
# FindSciGtest.cmake: Find the GTEST testing framework
#
# $Id: FindSciGtest.cmake 792 2015-04-17 14:07:44Z jrobcary $
#
# Copyright 2010-2015, Tech-X Corporation, Boulder, CO.
# See LICENSE file (EclipseLicense.txt) for conditions of use.
#
#
######################################################################

SciFindPackage(PACKAGE "Gtest"
              INSTALL_DIR ""  # empty?
              HEADERS "gtest.h"
              LIBRARIES "gtest"
              INCLUDE_SUBDIRS "include/gtest"
              LIBRARY_SUBDIRS "lib/${CXX_COMP_LIB_SUBDIR};lib"
              )

if (GTEST_FOUND)
  message(STATUS "Found gtest")
  set(HAVE_GTEST 1 CACHE BOOL "Whether have gtest")
else ()
  message(STATUS "Did not find gtest.  Use -DGTEST_DIR to specify the installation directory.")
  if (SciGtest_FIND_REQUIRED)
    message(FATAL_ERROR "Failed.")
  endif ()
endif ()
