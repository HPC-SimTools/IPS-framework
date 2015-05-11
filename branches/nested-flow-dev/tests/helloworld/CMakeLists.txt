######################################################################
#
# CMakeLists.txt for tests
#
# $Id:$
#
######################################################################

# Variable holding shared data
set(DATA
      hello_world.ips
)
set(PYSCRIPTS
      hello_driver.py hello_worker.py hello_worker_task_pool.py 
)
set(SHSCRIPTS
      test_ips.sh
)
include(${CMAKE_SOURCE_DIR}/tests/CmakeTests.cmake)
