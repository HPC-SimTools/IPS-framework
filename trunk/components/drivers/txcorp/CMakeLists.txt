######################################################################
#
# CMakeLists.txt for txcorp drivers
#
# $Id$
#
######################################################################

# Variable holding executable driver scripts
set(SCRIPTS
      txcorp_driver.py run_tx.sh rf_power_control.conf model_epa_input.nml
      model_RF_IC_input.nml README
)

# Installing executable scripts
install(PROGRAMS
  ${SCRIPTS}
  DESTINATION components/drivers/txcorp
  PERMISSIONS OWNER_READ OWNER_EXECUTE OWNER_WRITE
              GROUP_READ GROUP_EXECUTE ${TX_GROUP_WRITE} ${TX_WORLD_PERMS}
)

# Link data and scripts to build dir
if (NOT WIN32)
add_custom_target(txcorp-driver-scripts-stamp ALL
  COMMAND ${CMAKE_SOURCE_DIR}/CMake/mklinks.sh txutils-scripts-stamp
    ${CMAKE_CURRENT_SOURCE_DIR} ${DATA} ${SCRIPTS}
  COMMAND chmod a+x *.py
)
endif ()
