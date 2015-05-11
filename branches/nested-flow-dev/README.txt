
Building IPS with CMake using shell script 
============================================

In this example, we will "build out of place".  The building also works
if you stay in the top level directory.

From the top level directory::
  
  mkdir build
  cd build
  ../bin/ipsconfig.sh

This creates a config.sh which is meant to easily edit your cmake
configuration.  Assuming that you just want to use the default::

  ./config.sh

After configuring, to build IPS and run the tests::
  
  make
  make test
  
It is highly recommended to install the IPS in a location separate from 
the build tree using the command

  make install

If you have sphinx-build in your path and cmake detected it, then the
following command will build the documentation::

  make docs

The documentation may be found at docs/html/index.html.  The
tests are located in the tests subdirectory.

Things to check after building
============================================

The share directory contains platform.conf and component-generic.conf.
You can edit these if the values are not correct.  The values are
generally meant to be passed in as discussed in the next section, but it
can be easier to just edit these files.


Advanced building with CMake
============================================

The config.sh is meant to be easily editted to create more complicated
configuration commands.  For example::

  cmake \
    -DCMAKE_INSTALL_PREFIX:PATH=/usr/local/ips \
    -DPHYS_BIN_ROOT=/usr/local/swimroot/bin \
    -DCMAKE_VERBOSE_MAKEFILE:BOOL=TRUE \
    -DCMAKE_INSTALL_ALWAYS:BOOL=TRUE \
    -DCMAKE_BUILD_TYPE:STRING=RELEASE \
    -DSUPRA_SEARCH_PATH='/usr/local;/contrb' \
    $PWD/..

SUPRA_SEARCH_PATH is a list of directories to search for where to find
things like sphinx which is used to build the documentation.

