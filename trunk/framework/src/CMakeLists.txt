######################################################################
#
# CMakeLists.txt for txutils
#
# $Id: CMakeLists.txt 758 2011-06-27 22:35:44Z cary $
#
######################################################################

# Variable holding executable scripts
set(SCRIPTS
      cca_es_spec.py component.py componentRegistry.py configobj.py
      configurationManager.py create_batch_script.py dataManager.py
      debug.py eventService.py eventServiceProxy.py ftbBridge.py ips.py
      ipsExceptions.py ipsLogging.py ipsTiming.py ipsutil.py ips-config.py
      ips_es_spec.py messages.py node_structure.py portalBridge.py
      resourceHelper.py resourceManager.py sendPost.py services.py
      taskManager.py test_ips.py test_resource_parsing.py topicManager.py
)

# Installing executable scripts
install(PROGRAMS
  ${SCRIPTS}
  DESTINATION bin
  PERMISSIONS OWNER_READ OWNER_EXECUTE OWNER_WRITE
              GROUP_READ GROUP_EXECUTE ${TX_GROUP_WRITE} ${TX_WORLD_PERMS}
)

# Link data and scripts to build dir
if (NOT WIN32)
add_custom_target(txutils-scripts-stamp ALL
  COMMAND ${CMAKE_SOURCE_DIR}/CMake/mklinks.sh txutils-scripts-stamp
    ${CMAKE_CURRENT_SOURCE_DIR} ${DATA} ${SCRIPTS}
  COMMAND chmod a+x *.sh *.py
)
endif ()

