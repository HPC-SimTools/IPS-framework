from ipsframework import Component


class init_dataManager(Component):
    def step(self, timestamp=0.0, **keywords):
        state_file_list = self.services.get_config_param('STATE_FILES').split(' ')

        for state_file in state_file_list:
            with open(state_file, 'w') as f:
                if '100' in state_file:
                    f.write('100\n')
                else:
                    f.write('1\n')

        self.services.update_state()
