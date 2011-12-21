######################################################################
#
# CMakeLists.txt for tests
#
# $Id:$
#
######################################################################
# Variable holding shared data
set(DATA
      basic_serial1.ips 
      basic_serial2.ips 
)
set(PYSCRIPTS
)
set(SHSCRIPTS
      test_ips.sh
)
include(${CMAKE_SOURCE_DIR}/tests/CmakeTests.cmake)

