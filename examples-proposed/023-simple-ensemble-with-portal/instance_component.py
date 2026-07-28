"""
Component to be stepped in instance
"""

import csv
import itertools
import json
import sys
from time import time
from typing import Any

from ipsframework import Component
from ipsframework.resourceHelper import get_platform_info


def generate_fake_data(timestamp: float, base_x: float, base_y: float, word: str) -> dict[str, Any]:
    x_data = []
    y_data = []

    for idx, perm in enumerate(itertools.permutations(word)):
        x = timestamp + (idx + 1) * base_x
        y = timestamp + (idx + 1) * base_y
        for ch_idx, character in enumerate(perm):
            shrink_factor = 1 if ch_idx % 2 == 0 else -1
            x = abs(x + ((ord(character) + ch_idx + 1) * shrink_factor))
            y = abs(y + ((ord(character) * (ch_idx + 1)) * shrink_factor))
            x_data.append(x)
            y_data.append(y)

    return {
        'base_x': base_x,
        'base_y': base_y,
        'word': word,
        'x_data': x_data,
        'y_data': y_data,
    }


class InstanceComponent(Component):
    def step(self, timestamp: float = 0.0, **keywords):
        start = time()

        # ENSEMBLE_INSTANCE is a special IPS variable that contains the
        # string uniquely identifying this instance.  Each instance will have
        # the `run_ensemble()` `name` argument prepended to a unique number
        # for each instance.  E.g., ENSEMBLE_INSTANCE might be "MY_INSTANCE_23".
        instance_id = self.services.get_config_param('ENSEMBLE_INSTANCE')
        self.services.info(f'{instance_id}: Start of step of instance component.')

        # Echo the parameters we're expecting, A, B, and C
        self.services.info(
            f'{instance_id}: instance component parameters: base_x={self.base_x}, base_y={self.base_y}, word={self.word}'
        )

        # generate some fake data and save it
        data_fname = f'generated_{timestamp}.json'
        data = generate_fake_data(timestamp, float(self.base_x), float(self.base_y), self.word)
        with open(data_fname, 'w') as fd:
            json.dump(data, fd)

        # Save some per-component stats
        stats_fname = f'stats_{timestamp}.csv'
        run_env = get_platform_info()

        with open(stats_fname, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['instance', 'executable', 'hostname', 'pid', 'core', 'start', 'end'])
            writer.writerow(
                [
                    instance_id,
                    sys.argv[0],
                    run_env['hostname'],
                    run_env['pid'],
                    run_env['core_id'],
                    start,
                    time(),
                ]
            )

        try:
            self.services.add_analysis_data_files([data_fname, stats_fname], timestamp)
        except Exception:
            print('did not add data files to portal, check logs')

        self.services.info(f'{instance_id}: End of step of instance component.')
