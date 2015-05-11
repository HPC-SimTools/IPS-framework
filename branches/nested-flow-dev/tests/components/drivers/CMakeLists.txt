######################################################################
#
# CMakeLists.txt for vpunit
#
# $Id: CMakeLists.txt 18580 2011-10-19 20:01:46Z amyx $
#
######################################################################

set(PYSCRIPTS
        basic_concurrent1.py basic_concurrent2.py basic_concurrent3.py
        basic_serial1.py basic_serial2.py basic_serial3.py
        mcmd_driver.py workstation_test.py
)
include(${CMAKE_SOURCE_DIR}/tests/CmakeTests.cmake)
