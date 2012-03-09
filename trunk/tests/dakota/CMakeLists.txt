######################################################################
#
# CMakeLists.txt for tests
#
# $Id:$
#
######################################################################
# Variable holding shared data
set(DATA
      dakota_test_Rosenbrock.ips
      dakota_test_Rosenbrock.in
)
set(SHSCRIPTS
      test_ips.sh
)
set(PYSCRIPTS
      dakota_test_Rosenbrock.py
)
include(${CMAKE_SOURCE_DIR}/tests/CmakeTests.cmake)


