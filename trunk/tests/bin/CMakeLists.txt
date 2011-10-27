######################################################################
#
# CMakeLists.txt for tests
#
# $Id:$
#
######################################################################

set(SCRIPTS
    py_launch.py makefile test_parallel_codes
)

install(PROGRAMS 
    ${SCRIPTS}
    DESTINATION bin/tests/bin
    PERMISSIONS OWNER_READ OWNER_EXECUTE OWNER_WRITE
                GROUP_READ GROUP_EXECUTE ${TX_GROUP_WRITE} ${TX_WORLD_PERMS}
)

if (NOT WIN32)
add_custom_target(tests-bin-scripts-stamp ALL
    COMMAND ${CMAKE_SOURCE_DIR}/CMake/mklinks.sh txutils-scripts-stamp
      ${CMAKE_CURRENT_SOURCE_DIR} ${DATA} ${SCRIPTS}
    COMMAND chmod a+x *.py
)
endif ()
