from ipsframework import Component


class driver(Component):
    def step(self, timestamp=0.0, **keywords):
        ports = self.services.get_config_param('PORTS')
        port_names = ports['NAMES'].split()

        port_dict = {}
        port_id_list = []
        for port_name in port_names:
            if port_name in ['DRIVER']:
                continue
            port = self.services.get_port(port_name)
            port_dict[port_name] = port
            port_id_list.append(port)

        for port_name in port_names:
            if port_name in ['INIT', 'DRIVER']:
                continue
            self.services.call(port_dict[port_name], 'init', 0)

        for port_name in port_names:
            if port_name in ['INIT', 'DRIVER']:
                continue
            self.services.call(port_dict[port_name], 'step', 0)

        for port_name in port_names:
            if port_name in ['INIT', 'DRIVER']:
                continue
            self.services.call(port_dict[port_name], 'finalize', 0)
