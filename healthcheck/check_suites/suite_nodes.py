import functools
import math
import re

from healthcheck.api_fetcher import ApiFetcher
from healthcheck.check_suites.base_suite import BaseCheckSuite
from healthcheck.common_funcs import to_gb, to_percent, to_ms
from healthcheck.remote_executor import RemoteExecutor


class NodeChecks(BaseCheckSuite):
    """Nodes - setup, configuration and usage"""

    def __init__(self, _config):
        """
        :param _config: The configuration.
        """
        super().__init__(_config)
        self.api = ApiFetcher.instance(_config)
        self.rex = RemoteExecutor.instance(_config)

    def run_connection_checks(self):
        self.api.check_connection()
        self.rex.check_connection()

    def check_os_version(self, *_args, **_kwargs):
        """get OS version of each node"""
        rsps = self.rex.exec_broad('cat /etc/os-release | grep PRETTY_NAME')
        matches = [re.match(r'^PRETTY_NAME="(.*)"$', rsp.result()) for rsp in rsps]
        os_versions = [match.group(1) for match in matches]

        kwargs = {f'node:{self.api.get_uid(self.rex.get_addr(rsp.target))}': os_version for rsp, os_version
                  in zip(rsps, os_versions)}
        return None, kwargs

    def check_software_version(self, *_args, **_kwargs):
        """get RS version of each node"""
        node_ids = self.api.get_values('nodes', 'uid')
        software_versions = self.api.get_values('nodes', 'software_version')

        kwargs = {f'node:{node_id}': software_version for node_id, software_version in zip(node_ids, software_versions)}
        return None, kwargs

    def check_log_file_path(self, *_args, **_kwargs):
        """check if log file path is not on root filesystem"""
        rsps = self.rex.exec_broad('sudo df -h /var/opt/redislabs/log')
        matches = [re.match(r'^([\w+/]+)\s+.*$', rsp.result().split('\n')[1], re.DOTALL) for rsp in rsps]
        log_file_paths = [match.group(1) for match in matches]

        result = any(['/dev/root' not in log_file_path for log_file_path in log_file_paths])
        kwargs = {f'node:{self.api.get_uid(self.rex.get_addr(rsp.target))}': log_file_path for
                  rsp, log_file_path in zip(rsps, log_file_paths)}
        return result, kwargs

    def check_ephemeral_storage_path(self, *_args, **_kwargs):
        """check if ephemeral storage path is not on root filesystem"""
        storage_paths = self.api.get_values('nodes', 'ephemeral_storage_path')
        rsps = self.rex.exec_broad(f'sudo df -h {storage_paths[0]}')
        matches = [re.match(r'^([\w+/]+)\s+.*$', rsp.result().split('\n')[1], re.DOTALL) for rsp in rsps]
        file_paths = [match.group(1) for match in matches]

        result = any(['/dev/root' not in tmp_file_path for tmp_file_path in file_paths])
        kwargs = {f'node:{self.api.get_uid(self.rex.get_addr(rsp.target))}': tmp_file_path for
                  rsp, tmp_file_path in zip(rsps, file_paths)}
        return result, kwargs

    def check_persistent_storage_path(self, *_args, **_kwargs):
        """check if persistent storage path is not on root filesystem"""
        storage_paths = self.api.get_values('nodes', 'persistent_storage_path')
        rsps = self.rex.exec_broad(f'sudo df -h {storage_paths[0]}')
        matches = [re.match(r'^([\w+/]+)\s+.*$', rsp.result().split('\n')[1], re.DOTALL) for rsp in rsps]
        file_paths = [match.group(1) for match in matches]

        result = any(['/dev/root' not in tmp_file_path for tmp_file_path in file_paths])
        kwargs = {f'node:{self.api.get_uid(self.rex.get_addr(rsp.target))}': tmp_file_path for
                  rsp, tmp_file_path in zip(rsps, file_paths)}
        return result, kwargs

    def check_swappiness(self, *_args, **_kwargs):
        """check if swappiness is disabled on each node"""
        rsps = self.rex.exec_broad('grep swap /etc/sysctl.conf || echo inactive')
        swappinesses = [rsp.result() for rsp in rsps]

        result = any([swappiness == 'inactive' for swappiness in swappinesses])
        kwargs = {f'node:{self.api.get_uid(self.rex.get_addr(rsp.target))}': swappiness for rsp, swappiness
                  in zip(rsps, swappinesses)}
        return result, kwargs

    def check_transparent_hugepages(self, *_args, **_kwargs):
        """check if THP is disabled on each node"""
        rsps = self.rex.exec_broad('cat /sys/kernel/mm/transparent_hugepage/enabled')
        transparent_hugepages = [rsp.result() for rsp in rsps]

        result = all(transparent_hugepage == 'always madvise [never]' for transparent_hugepage in transparent_hugepages)
        kwargs = {f'node:{self.api.get_uid(self.rex.get_addr(rsp.target))}': transparent_hugepage for
                  rsp, transparent_hugepage in zip(rsps, transparent_hugepages)}
        return result, kwargs

    def check_rlcheck_result(self, *_args, **_kwargs):
        """check if `rlcheck` has errors"""
        rsps = self.rex.exec_broad('sudo /opt/redislabs/bin/rlcheck')
        failed = [(re.findall(r'FAILED', rsp.result().strip(), re.MULTILINE), rsp.target) for rsp in rsps]
        errors = sum([len(f[0]) for f in failed])

        return not errors, {f'node:{self.api.get_uid(self.rex.get_addr(f[1]))}': len(f[0]) for f in failed}

    def check_cnm_ctl_status(self, *_args, **_kwargs):
        """check if `cnm_ctl status` has errors"""
        rsps = self.rex.exec_broad('sudo /opt/redislabs/bin/cnm_ctl status')
        not_running = [(re.findall(r'^((?!RUNNING).)*$', rsp.result(), re.MULTILINE), rsp.target) for rsp in rsps]
        sum_not_running = sum([len(r[0]) for r in not_running])

        return sum_not_running == 0, {f'node:{self.api.get_uid(self.rex.get_addr(n_r[1]))}': len(n_r[0]) for
                                      n_r in not_running}

    def check_supervisorctl_status(self, *_args, **_kwargs):
        """check if `supervisorctl status` has errors"""
        rsps = self.rex.exec_broad('sudo /opt/redislabs/bin/supervisorctl status')
        not_running = [(re.findall(r'^((?!RUNNING).)*$', rsp.result(), re.MULTILINE), rsp.target) for rsp in rsps]
        sum_not_running = sum([len(r[0]) for r in not_running])

        return sum_not_running == 1 * len(rsps), {
            f'node:{self.api.get_uid(self.rex.get_addr(r[1]))}': len(r[0]) - 1 for r in not_running}

    def check_errors_in_install_log(self, *_args, **_kwargs):
        """check if `cat install.log` has errors"""
        rsps = self.rex.exec_broad('grep error /var/opt/redislabs/log/install.log || echo ""')
        errors = sum([len(rsp.result()) for rsp in rsps])

        return not errors, {f'node:{self.api.get_uid(self.rex.get_addr(rsp.target))}': len(rsp.result()) for
                            rsp in rsps}

    def check_network_link(self, *_args, **_kwargs):
        """get network link speed between nodes"""
        cmd_targets = []
        for source in self.rex.get_targets():
            for target, address in self.rex.get_addrs().items():
                if source == target:
                    continue
                cmd_targets.append((f'ping -c 4 {address}', source))

        # calculate averages
        _min, avg, _max, mdev = .0, .0, .0, .0
        futures = self.rex.exec_multi(cmd_targets)
        key = 'rtt min/avg/max/mdev'
        for future in futures:
            lines = future.result().split('\n')
            key = lines[-1:][0].split(' = ')[0]
            parts = lines[-1:][0].split(' = ')[1].split('/')
            _min = min(float(parts[0]), _min) if _min else float(parts[0])
            avg += float(parts[1])
            _max = max(float(parts[2]), _max)
            mdev += float(parts[3].split(' ')[0])

        avg /= len(futures)
        mdev /= len(futures)

        kwargs = {key: '{}/{}/{}/{} ms'.format(to_ms(_min), to_ms(avg), to_ms(_max), to_ms(mdev))}
        return None, kwargs

    def check_open_ports(self, *_args, **_kwargs):
        """check open TCP ports of each node"""
        cmd_targets = []
        ports = [3333, 3334, 3335, 3336, 3337, 3338, 3339, 8001, 8070, 8080, 8443, 9443, 36379]
        cmd = \
'''python -c "import socket; socket.create_connection(('"'"'{0}'"'"', {1}))" 2> /dev/null || echo '"'"'{0}:{1}'"'"' '''

        for port in ports:
            for source in self.rex.get_targets():
                for external, internal in self.rex.get_addrs().items():
                    if source == external:
                        continue
                    cmd_targets.append((cmd.format(internal, port), source))

        kwargs = {}
        futures = self.rex.exec_multi(cmd_targets)
        for future in futures:
            failed = future.result()
            if failed:
                node_name = f'node:{self.api.get_uid(self.rex.get_addr(future.target))}'
                if node_name not in kwargs:
                    kwargs[node_name] = []
                kwargs[node_name].append(failed)

        return not kwargs, kwargs if kwargs else {'open': 'all'}

    def check_cpu_usage(self, *_args, **_kwargs):
        """check CPU usage (min/avg/max/dev) of each node"""
        kwargs = {}
        results = {}

        # get quorum-only node
        nodes = self.api.get('nodes')
        rsps = [self.rex.exec_uni(f'sudo /opt/redislabs/bin/rladmin info node {node["uid"]}',
                                  self.rex.get_targets()[0]) for node in nodes]
        matches = [re.match(r'^.*quorum only: (\w+).*$', rsp, re.DOTALL) for rsp in rsps]
        quorum_onlys = list(map(lambda x: x[0]['uid'], filter(lambda x: x[1].group(1) == 'enabled', zip(nodes, matches))))

        for stat in self.api.get('nodes/stats'):
            ints = stat['intervals']
            uid = stat['uid']

            # calculate minimum
            minimum = min((1 - i['cpu_idle']) for i in filter(lambda x: x.get('cpu_idle'), ints))

            # calculate average
            cpu_idles = list(filter(lambda x: x.get('cpu_idle'), ints))
            sum_cpu_usage = sum((1 - i['cpu_idle']) for i in cpu_idles)
            average = sum_cpu_usage/len(cpu_idles)

            # calculate maximum
            maximum = max((1 - i['cpu_idle']) for i in filter(lambda x: x.get('cpu_idle'), ints))

            # calculate std deviation
            q_sum = functools.reduce(lambda x, y: x + pow((1 - y['cpu_idle']) - average, 2), cpu_idles, 0)
            std_dev = math.sqrt(q_sum / len(cpu_idles))

            node_name = f'node:{uid}'
            if uid in quorum_onlys:
                node_name += ' (quorum only)'

            results[node_name] = maximum > .8
            kwargs[node_name] = '{}/{}/{}/{} %'.format(to_percent(minimum),
                                                       to_percent(average),
                                                       to_percent(maximum),
                                                       to_percent(std_dev))

        return not any(results.values()), kwargs

    def check_ram_usage(self, *_args, **_kwargs):
        """check RAM usage (min/avg/max/dev) of each node"""
        kwargs = {}
        results = {}

        # get quorum-only node
        nodes = self.api.get('nodes')
        rsps = [self.rex.exec_uni(f'sudo /opt/redislabs/bin/rladmin info node {node["uid"]}',
                                  self.rex.get_targets()[0]) for node in nodes]
        matches = [re.match(r'^.*quorum only: (\w+).*$', rsp, re.DOTALL) for rsp in rsps]
        quorum_onlys = list(map(lambda x: x[0]['uid'], filter(lambda x: x[1].group(1) == 'enabled', zip(nodes, matches))))

        for stat in self.api.get('nodes/stats'):
            ints = stat['intervals']
            uid = stat['uid']

            # calculate minimum
            minimum_available = min(i['free_memory'] for i in filter(lambda x: x.get('free_memory'), ints))

            # calculate average
            free_mems = list(filter(lambda x: x.get('free_memory'), ints))
            sum_free_mem = sum(i['free_memory'] for i in free_mems)
            average_available = sum_free_mem/len(free_mems)

            # calculate maximum
            maximum_available = max(i['free_memory'] for i in filter(lambda x: x.get('free_memory'), ints))

            # calculate std deviation
            q_sum = functools.reduce(lambda x, y: x + pow(y['free_memory'] - average_available, 2), free_mems, 0)
            std_dev = math.sqrt(q_sum / len(free_mems))

            total_mem = self.api.get_value(f'nodes/{uid}', 'total_memory')

            node_name = f'node:{uid}'
            if uid in quorum_onlys:
                node_name += ' (quorum only)'

            results[node_name] = minimum_available < (total_mem * 2/3)
            kwargs[node_name] = '{}/{}/{}/{} GB'.format(to_gb(total_mem - maximum_available),
                                                        to_gb(total_mem - average_available),
                                                        to_gb(total_mem - minimum_available),
                                                        to_gb(std_dev))

        return not any(results.values()), kwargs

    def check_ephemeral_storage_usage(self, *_args, **_kwargs):
        """get ephemeral storage usage (min/avg/max/dev) of each node"""
        kwargs = {}

        # get quorum-only node
        nodes = self.api.get('nodes')
        rsps = [self.rex.exec_uni(f'sudo /opt/redislabs/bin/rladmin info node {node["uid"]}',
                                  self.rex.get_targets()[0]) for node in nodes]
        matches = [re.match(r'^.*quorum only: (\w+).*$', rsp, re.DOTALL) for rsp in rsps]
        quorum_onlys = list(
            map(lambda x: x[0]['uid'], filter(lambda x: x[1].group(1) == 'enabled', zip(nodes, matches))))

        for stat in self.api.get('nodes/stats'):
            ints = stat['intervals']
            uid = stat['uid']

            # calculate minimum
            minimum_available = min(
                i['ephemeral_storage_avail'] for i in filter(lambda x: x.get('ephemeral_storage_avail'), ints))

            # calculate average
            ephemeral_storage_avails = list(filter(lambda x: x.get('ephemeral_storage_avail'), ints))
            sum_ephemeral_storage_avail = sum(i['ephemeral_storage_avail'] for i in ephemeral_storage_avails)
            average_available = sum_ephemeral_storage_avail / len(ephemeral_storage_avails)

            # calculate maximum
            maximum_available = max(
                i['ephemeral_storage_avail'] for i in filter(lambda x: x.get('ephemeral_storage_avail'), ints))

            # calculate std deviation
            q_sum = functools.reduce(
                lambda x, y: x + pow(y['ephemeral_storage_avail'] - average_available, 2),
                ephemeral_storage_avails, 0)
            std_dev = math.sqrt(q_sum / len(ephemeral_storage_avails))

            ephemeral_storage_size = self.api.get_value(f'nodes/{uid}', 'ephemeral_storage_size')

            node_name = f'node:{uid}'
            if uid in quorum_onlys:
                node_name += ' (quorum only)'

            kwargs[node_name] = '{}/{}/{}/{} GB'.format(to_gb(ephemeral_storage_size - maximum_available),
                                                        to_gb(ephemeral_storage_size - average_available),
                                                        to_gb(ephemeral_storage_size - minimum_available),
                                                        to_gb(std_dev))

        return None, kwargs

    def check_persistent_storage_usage(self, *_args, **_kwargs):
        """get persistent storage usage (min/avg/max/dev) of each node"""
        kwargs = {}

        # get quorum-only node
        nodes = self.api.get('nodes')
        rsps = [self.rex.exec_uni(f'sudo /opt/redislabs/bin/rladmin info node {node["uid"]}',
                                  self.rex.get_targets()[0]) for node in nodes]
        matches = [re.match(r'^.*quorum only: (\w+).*$', rsp, re.DOTALL) for rsp in rsps]
        quorum_onlys = list(
            map(lambda x: x[0]['uid'], filter(lambda x: x[1].group(1) == 'enabled', zip(nodes, matches))))

        for stat in self.api.get('nodes/stats'):
            ints = stat['intervals']
            uid = stat['uid']

            # calculate minimum
            minimum_available = min(
                i['persistent_storage_avail'] for i in filter(lambda x: x.get('persistent_storage_avail'), ints))

            # calculate average
            persistent_storage_avails = list(filter(lambda x: x.get('persistent_storage_avail'), ints))
            sum_persistent_storage_avail = sum(i['persistent_storage_avail'] for i in persistent_storage_avails)
            average_available = sum_persistent_storage_avail / len(persistent_storage_avails)

            # calculate maximum
            maximum_available = max(
                i['persistent_storage_avail'] for i in filter(lambda x: x.get('persistent_storage_avail'), ints))

            # calculate std deviation
            q_sum = functools.reduce(
                lambda x, y: x + pow(y['persistent_storage_avail'] - average_available, 2),
                persistent_storage_avails, 0)
            std_dev = math.sqrt(q_sum / len(persistent_storage_avails))

            persistent_storage_size = self.api.get_value(f'nodes/{uid}', 'persistent_storage_size')

            node_name = f'node:{uid}'
            if uid in quorum_onlys:
                node_name += ' (quorum only)'

            kwargs[node_name] = '{}/{}/{}/{} GB'.format(to_gb(persistent_storage_size - maximum_available),
                                                        to_gb(persistent_storage_size - average_available),
                                                        to_gb(persistent_storage_size - minimum_available),
                                                        to_gb(std_dev))

        return None, kwargs
