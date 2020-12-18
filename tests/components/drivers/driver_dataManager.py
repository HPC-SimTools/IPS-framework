from ipsframework import Component


class driver_dataManager(Component):
    def step(self, timestamp=0.0):
        self.services.stage_state()

        state_file_list = self.services.get_config_param('STATE_FILES').split(' ')

        for state_file in state_file_list:
            with open(state_file, 'r') as f:
                data = int(f.readline())

            data += 1

            with open(state_file, 'w') as f:
                f.write(f'{data}\n')

        self.services.update_state()
