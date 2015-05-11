######################################################################
#
# CMakeLists.txt for docs
#
# $Id: CMakeLists.txt 1138 2011-01-28 00:25:57Z swsides $
#
######################################################################

# Platform
configure_file(platform.conf.in  platform.conf)
configure_file(component-generic.conf.in  component-generic.conf)
install(FILES ${CMAKE_BINARY_DIR}/share/platform.conf
              ${CMAKE_BINARY_DIR}/share/component-generic.conf 
        DESTINATION  ${CMAKE_INSTALL_PREFIX}/share)
