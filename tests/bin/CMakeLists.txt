######################################################################
#
# CMakeLists.txt for tests
#
# $Id:$
#
######################################################################
set(DATA test_parallel_codes)

#SEK: Worry about this later
add_executable(faulty_serial_sleep faulty_serial_sleep.c)
add_executable(serial_sleep serial_sleep.c)

if(parallel)
add_executable(faulty_parallel_sleep faulty_parallel_sleep.c)
add_executable(parallel_sleep parallel_sleep.c)
endif()

set(PYSCRIPTS py_launch.py)

include(${CMAKE_SOURCE_DIR}/tests/CmakeTests.cmake)
