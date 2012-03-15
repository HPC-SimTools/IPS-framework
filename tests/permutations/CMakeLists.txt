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
)
set(SHSCRIPTS
      setup_test.sh
)
set(TESTPYSCRIPTS
      test_ips.py 
)
set(PYSCRIPTS
      test_parameterized_cases.py test_permutations.py
)
include(${CMAKE_SOURCE_DIR}/tests/CmakeTests.cmake)

