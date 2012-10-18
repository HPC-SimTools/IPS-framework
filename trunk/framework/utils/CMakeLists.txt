######################################################################
#
# CMakeLists.txt for txutils
#
# $Id: CMakeLists.txt 758 2011-06-27 22:35:44Z cary $
#
######################################################################

# Variable holding executable scripts
set(SCRIPTS
      BeautifulSoup.py 
      animate_parareal_converge.py animate_parareal_tasks.py
      batch_mgmt_script.py convert_log.py exec_timer.py
      exec_timer_parareal.py gen_stddev.py physics_timer.py
      read_dict.py serial_timer.py 
)

# Installing executable scripts
install(PROGRAMS
  ${SCRIPTS}
  DESTINATION bin
  PERMISSIONS OWNER_READ OWNER_EXECUTE OWNER_WRITE
              GROUP_READ GROUP_EXECUTE ${SCI_GROUP_WRITE} ${SCI_WORLD_PERMS}
)

# Link data and scripts to build dir
if (NOT WIN32)
add_custom_target(utils-scripts-stamp ALL
  COMMAND ${CMAKE_SOURCE_DIR}/scimake/mklinks.sh txutils-scripts-stamp
    ${CMAKE_CURRENT_SOURCE_DIR} ${DATA} ${SCRIPTS}
  COMMAND chmod a+x *.py
)
endif ()
