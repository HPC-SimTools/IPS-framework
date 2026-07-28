"""
The platform configuration file is used to specify the resources available
to the framework for a given platform.
"""

# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import os
import sys

from .messages import Message


def get_share_and_platform(platform_file_name: str | None, ips_path_name: str) -> tuple[str, str]:
    if platform_file_name:
        return platform_file_name, ''
    else:
        ips_p_dir0 = os.path.dirname(ips_path_name)
        ips_p_dir1 = os.path.dirname(ips_p_dir0)
        ips_p_dir2 = os.path.dirname(ips_p_dir1)
        # This is if we've installed it
        pconf = os.path.join('share', 'platform.conf')
        if os.path.exists(os.path.join(ips_p_dir1, pconf)):
            ips_share_dir = os.path.join(ips_p_dir1, 'share')
        # This is looking in the build directory.
        elif os.path.exists(os.path.join(ips_p_dir2, pconf)):
            ips_share_dir = os.path.join(ips_p_dir2, 'share')
        else:
            print('Need to specify a platform file', file=sys.stderr)
            sys.exit(Message.FAILURE)
        platform_file_name = os.path.join(ips_share_dir, 'platform.conf')
        return os.path.abspath(platform_file_name), ips_share_dir
