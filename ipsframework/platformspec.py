# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import os
import sys
from .messages import Message


def get_share_and_platform(platform_file_name, ipsPathName):
    if platform_file_name:
        return platform_file_name, ''
    else:
        ipsPDir0 = os.path.dirname(ipsPathName)
        ipsPDir1 = os.path.dirname(ipsPDir0)
        ipsPDir2 = os.path.dirname(ipsPDir1)
        # This is if we've installed it
        pconf = os.path.join('share', 'platform.conf')
        if os.path.exists(os.path.join(ipsPDir1, pconf)):
            ipsShareDir = os.path.join(ipsPDir1, 'share')
        # This is looking in the build directory.
        elif os.path.exists(os.path.join(ipsPDir2, pconf)):
            ipsShareDir = os.path.join(ipsPDir2, 'share')
        else:
            print("Need to specify a platform file")
            sys.exit(Message.FAILURE)
        platform_file_name = os.path.join(ipsShareDir, 'platform.conf')
        return os.path.abspath(platform_file_name), ipsShareDir
