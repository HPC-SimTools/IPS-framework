######################################################################
#
# This is a little snippet for all of the tests.
#
# $Id:$
#
######################################################################

# SHSCRIPTS should be executed before TESTPYSCRIPTS because
# they will sometimes be used to touch files or prepare inputs
# for the tests
if (DEFINED SHSCRIPTS)
foreach (targ ${SHSCRIPTS})
      get_filename_component(dirname ${CMAKE_CURRENT_BINARY_DIR} NAME_WE)
      add_test(${dirname}-${targ} ${targ})
endforeach ()
endif ()

# TESTPYSCRIPTS are specifically the scripts that are associated 
# with running a test, and should not include additional test
# component classes or other such PYSCRIPT utility classes
if (DEFINED TESTPYSCRIPTS)
foreach (targ ${TESTPYSCRIPTS})
      get_filename_component(dirname ${CMAKE_CURRENT_BINARY_DIR} NAME_WE)
      add_test(${dirname}-${targ} python ${targ})
endforeach ()
endif ()


install(PROGRAMS 
    ${PYSCRIPTS} ${TESTPYSCRIPTS} ${SHSCRIPTS}
    DESTINATION bin/tests/bin
    PERMISSIONS OWNER_READ OWNER_EXECUTE OWNER_WRITE
                GROUP_READ GROUP_EXECUTE ${SCI_GROUP_WRITE} ${SCI_WORLD_PERMS}
)

if (NOT WIN32)
get_filename_component(dirname ${CMAKE_CURRENT_BINARY_DIR} NAME_WE)
add_custom_target(tests-${dirname}-scripts-stamp ALL
    COMMAND ${CMAKE_SOURCE_DIR}/scimake/mklinks.sh txutils-scripts-stamp
      ${CMAKE_CURRENT_SOURCE_DIR} ${DATA} ${PYSCRIPTS}
    COMMAND ${CMAKE_SOURCE_DIR}/scimake/mklinks.sh txutils-scripts-stamp
      ${CMAKE_CURRENT_SOURCE_DIR} ${DATA} ${TESTPYSCRIPTS}
    COMMAND ${CMAKE_SOURCE_DIR}/scimake/mklinks.sh txutils-scripts-stamp
      ${CMAKE_CURRENT_SOURCE_DIR} ${DATA} ${SHSCRIPTS}
      #COMMAND chmod -f a+x *.py  *.sh
    #    COMMAND chmod a+x *.py *.sh
)
else ()
file(COPY ${PYSCRIPTS} DESTINATION ${CMAKE_CURRENT_BINARY_DIR})
file(COPY ${TESTPYSCRIPTS} DESTINATION ${CMAKE_CURRENT_BINARY_DIR})
file(COPY ${SHSCRIPTS} DESTINATION ${CMAKE_CURRENT_BINARY_DIR})
endif ()
