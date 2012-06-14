# Variable holding executable scripts
set(SCRIPTS
      cca_es_spec.py component.py componentRegistry.py configobj.py
      configurationManager.py create_batch_script.py dataManager.py
      debug.py eventService.py eventServiceProxy.py ftbBridge.py
      ips-config.py ips.py ipsExceptions.py ipsLogging.py ipsTiming.py
      ips_es_spec.py ipsutil.py messages.py node_structure.py
      portalBridge.py resourceHelper.py resourceManager.py
      runspaceInitComponent.py sendPost.py services.py taskManager.py
      checklist.py dakota_bridge.py ips_dakota_client.py ips_dakota_dynamic.py
      test_ips.py test_resource_parsing.py topicManager.py platform.py

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
add_custom_target(framework-scripts-stamp ALL
  COMMAND ${CMAKE_SOURCE_DIR}/scimake/mklinks.sh txutils-scripts-stamp
    ${CMAKE_CURRENT_SOURCE_DIR} ${DATA} ${SCRIPTS}
  COMMAND chmod a+x *.py
)
endif ()

