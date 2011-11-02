######################################################################
#
# CMakeLists.txt for docs
#
# $Id: CMakeLists.txt 1138 2011-01-28 00:25:57Z swsides $
#
######################################################################

# Platform
configure_file(platform.conf.in  platform.conf)
configure_file(components-generic.conf.in  components-generic.conf)
install(FILES platform.conf components-generic.conf DESTINATION  ${CMAKE_INSTALL_PREFIX}/share)
