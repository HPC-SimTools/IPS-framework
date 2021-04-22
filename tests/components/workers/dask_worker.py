from ipsframework import Component


class dask_worker(Component):
    def step(self, timestamp=0.0, **keywords):
        cmd = self.EXECUTABLE
        self.services.send_portal_event(event_type='COMPONENT_EVENT',
                                        event_comment=cmd)
        self.services.info("cmd = %s", cmd)
        cwd = self.services.get_working_dir()

        total_tasks = 4
        self.services.create_task_pool('pool')
        for i in range(total_tasks):
            kwargs = {}
            if self.TIMEOUT:
                kwargs['timeout'] = self.TIMEOUT
            if self.LOGFILE:
                kwargs['logfile'] = self.LOGFILE.format(i)
            if self.ERRFILE:
                kwargs['errfile'] = self.ERRFILE.format(i)

            self.services.add_task('pool', f'task_{i}',
                                   int(self.NPROC),
                                   cwd,
                                   cmd,
                                   self.VALUE if self.VALUE else f'{i}',
                                   **kwargs)
        nodes = self.services.get_config_param('NODES')
        ret_val = self.services.submit_tasks('pool', use_dask=True, dask_nodes=nodes)
        self.services.info('ret_val = %d', ret_val)
        exit_status = self.services.get_finished_tasks('pool')
        for i in range(total_tasks):
            task_name = f'task_{i}'
            self.services.info('{} {}'.format(task_name, exit_status.get(task_name)))
