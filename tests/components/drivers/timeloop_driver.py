from ipsframework import Component


class timeloop_driver(Component):
    def step(self, timestamp=0.0):
        super().step(timestamp)

        ports = self.services.get_config_param('PORTS')
        port_names = ports['NAMES'].split()

        timeloop = self.services.get_time_loop()

        port_dict = {}
        port_id_list = []
        for port_name in port_names:
            if port_name in ["DRIVER"]:
                continue
            port = self.services.get_port(port_name)
            port_dict[port_name] = port
            port_id_list.append(port)

        for port_name in port_names:
            if port_name in ['INIT', 'DRIVER']:
                continue
            self.services.call(port_dict[port_name], 'init', timeloop[0])

        for t in timeloop:
            self.services.update_time_stamp(t)
            for port_name in port_names:
                if port_name in ['INIT', 'DRIVER']:
                    continue
                self.services.call(port_dict[port_name], 'step', t)

            # self.services.stage_output_files(t, self.OUTPUT_FILES)
            self.services.checkpoint_components(port_id_list, t)
            self.checkpoint(t)

        for port_name in port_names:
            if port_name in ['INIT', 'DRIVER']:
                continue
            self.services.call(port_dict[port_name], 'finalize', timeloop[-1])

    def checkpoint(self, timestamp=0.0):
        self.services.log(f'checkpoint({timestamp})')
