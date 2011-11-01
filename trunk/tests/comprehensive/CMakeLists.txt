######################################################################
#
# CMakeLists.txt for tests
#
# $Id:$
#
######################################################################

# Variable holding shared data
set(DATA
   basic_concurrent1.conf basic_concurrent2.conf basic_concurrent3.conf
   basic_serial1.conf basic_serial2.conf basic_serial3.conf
   franklin.conf iter.conf jaguar.conf mhd.conf odin.conf
   sim.conf simple_platform.conf simple_sim.conf workstation.conf
)
set(PYSCRIPTS
      test_ips.py
)
include(${CMAKE_SOURCE_DIR}/tests/CmakeTests.cmake)

