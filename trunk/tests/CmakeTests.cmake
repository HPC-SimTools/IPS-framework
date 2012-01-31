######################################################################
#
# This is a little snippet for all of the tests.
#
# $Id:$
#
######################################################################

if (DEFINED PYSCRIPTS)
foreach (targ ${PYSCRIPTS})
      get_filename_component(dirname ${CMAKE_CURRENT_BINARY_DIR} NAME_WE)
      add_test(${dirname}-${targ} python ${targ})
endforeach ()
endif ()
if (DEFINED SHSCRIPTS)
foreach (targ ${SHSCRIPTS})
      add_test(${dirname}-${targ} ${targ})
endforeach ()
endif ()

install(PROGRAMS 
    ${PYSCRIPTS} ${SHSCRIPTS}
    DESTINATION bin/tests/bin
    PERMISSIONS OWNER_READ OWNER_EXECUTE OWNER_WRITE
                GROUP_READ GROUP_EXECUTE ${TX_GROUP_WRITE} ${TX_WORLD_PERMS}
)

if (NOT WIN32)
get_filename_component(dirname ${CMAKE_CURRENT_BINARY_DIR} NAME_WE)
add_custom_target(tests-${dirname}-scripts-stamp ALL
    COMMAND ${CMAKE_SOURCE_DIR}/CMake/mklinks.sh txutils-scripts-stamp
      ${CMAKE_CURRENT_SOURCE_DIR} ${DATA} ${PYSCRIPTS}
    COMMAND ${CMAKE_SOURCE_DIR}/CMake/mklinks.sh txutils-scripts-stamp
      ${CMAKE_CURRENT_SOURCE_DIR} ${DATA} ${SHSCRIPTS}
      #COMMAND chmod -f a+x *.py  *.sh
    #    COMMAND chmod a+x *.py *.sh
)
else ()
file(COPY ${PYSCRIPTS} DESTINATION ${CMAKE_CURRENT_BINARY_DIR})
file(COPY ${SHSCRIPTS} DESTINATION ${CMAKE_CURRENT_BINARY_DIR})
endif ()
