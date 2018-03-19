# - FindSciGsl: Module to find include directories and
#   libraries for Gsl.
#
# Module usage:
#   find_package(SciGsl ...)
#
# This module will define the following variables:
#  HAVE_GSL, GSL_FOUND = Whether libraries and includes are found
#  Gsl_INCLUDE_DIRS       = Location of Gsl includes
#  Gsl_LIBRARY_DIRS       = Location of Gsl libraries
#  Gsl_LIBRARIES          = Required libraries

######################################################################
#
# FindGsl: find includes and libraries for GSL
#
# $Id: FindSciGsl.cmake 792 2015-04-17 14:07:44Z jrobcary $
#
# Copyright 2010-2015, Tech-X Corporation, Boulder, CO.
# See LICENSE file (EclipseLicense.txt) for conditions of use.
#
#
######################################################################

SciFindPackage(PACKAGE "Gsl"
              INSTALL_DIR "gsl"
              HEADERS "gsl/gsl_math.h;gsl/gsl_sf_legendre.h"
              LIBRARIES "gsl;gslcblas"
              INCLUDE_SUBDIRS "include"
              LIBRARY_SUBDIRS "lib"
             )

if (GSL_FOUND)
  message(STATUS "Found Gsl")
  set(HAVE_GSL 1 CACHE BOOL "Whether have Gsl")
else ()
  message(STATUS "Did not find Gsl.  Use -DGSL_DIR to specify the installation directory.")
  if (SciGsl_FIND_REQUIRED)
    message(FATAL_ERROR "Failed.")
  endif ()
endif ()
