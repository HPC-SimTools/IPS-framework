######################################################################
#
# CMakeLists.txt for vpunit
#
# $Id: CMakeLists.txt 18580 2011-10-19 20:01:46Z amyx $
#
######################################################################

set(PYSCRIPTS
      XL_worker.py large_worker.py mcmd_worker.py medium_worker.py small_worker.py
   )

include(${CMAKE_SOURCE_DIR}/tests/CmakeTests.cmake)
