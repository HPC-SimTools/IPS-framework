######################################################################
#
# CMakeLists.txt for hello drivers
#
# $Id$
#
######################################################################

# Variable holding executable driver scripts
set(SCRIPTS
      hello_driver.py hello_worker.py hello_worker_task_pool.py
)

# Installing executable scripts
install(PROGRAMS
  ${SCRIPTS}
  DESTINATION components/drivers/hello
  PERMISSIONS OWNER_READ OWNER_EXECUTE OWNER_WRITE
              GROUP_READ GROUP_EXECUTE ${TX_GROUP_WRITE} ${TX_WORLD_PERMS}
)

# Link data and scripts to build dir
if (NOT WIN32)
add_custom_target(hello-driver-scripts-stamp ALL
  COMMAND ${CMAKE_SOURCE_DIR}/CMake/mklinks.sh txutils-scripts-stamp
    ${CMAKE_CURRENT_SOURCE_DIR} ${DATA} ${SCRIPTS}
  COMMAND chmod a+x *.py
)
endif ()
