######################################################################
#
# CMakeLists.txt for tests
#
# $Id:$
#
######################################################################
# Variable holding shared data
set(DATA
      basic_serial1_iter.conf 
)
set(PYSCRIPTS
      test_ips.py test_ips_iter.py 
      test_parameterized_cases.py test_permutations.py
)
set(SHSCRIPTS
      test_ips.sh
)
include(${CMAKE_SOURCE_DIR}/tests/CmakeTests.cmake)

