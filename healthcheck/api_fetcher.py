from healthcheck.common_funcs import http_get
from healthcheck.printer_funcs import print_msg, print_success, print_error


class ApiFetcher(object):
    """
    API-Fetcher class.
    """
    _instance = None

    def __init__(self, _config):
        """
        :param _config: The parsed configuration.
        """
        self.addr = _config['api']['addr']
        self.username = _config['api']['user']
        self.password = _config['api']['pass']
        self.cache = {}
        self.uids = {}
        self.connected = None

    @classmethod
    def inst(cls, _config):
        """
        Get singleton instance.

        :param _config: A dict with configuration values.
        :return: The ApiFetcher singleton.
        """
        if not cls._instance:
            cls._instance = ApiFetcher(_config)

        return cls._instance

    def check_connection(self):
        """
        Check API connection.
        """
        if self.connected is not None:
            return

        print_msg('checking API connection ...')
        try:
            addr = self.get_value('cluster', 'name')
            print_success(f'- successfully connected to {addr}')
            self.connected = True
        except Exception as e:
            print_error('could not connect to Redis Enterprise REST-API:', e)
            self.connected = False
        print_msg('')

    def get_uid(self, _internal_addr):
        """
        Get UID of node.

        :param _internal_addr: The internal address of the the node.
        :return: The UID of the node.
        """
        if not self.uids:
            self.uids = {node['addr']: node['uid'] for node in self.get('nodes')}

        return self.uids[_internal_addr]

    def get(self, _topic):
        """
        Get a topic.

        :param _topic: The topic, e.g. 'nodes'
        :return: The result dictionary.
        """
        return self._fetch(_topic)

    def get_with_value(self, _topic, _key, _value):
        """
        Get a topic with a given value.

        :param _topic: The topic, e.g. 'nodes'
        :param _key: The key, e.g. 'uid'
        :param _value: The value.
        :return: The result dictionary.
        """
        return filter(lambda x: x[_key] == _value, self._fetch(_topic))

    def get_value(self, _topic, _key):
        """
        Get a value from a topic.

        :param _topic: The topic, e.g. 'nodes'
        :param _key: The key of the value.
        :return: The value.
        """
        return self._fetch(_topic)[_key]

    def get_values(self, _topic, _key):
        """
        Get values from a topic.

        :param _topic: The topic, e.g. 'nodes'
        :param _key: The key of the values.
        :return: A list with values.
        """
        return [node[_key] for node in self._fetch(_topic)]

    def get_number_of_values(self, _topic):
        """
        Get the amount of values from a topic.

        :param _topic: The topic, e.g. 'nodes'
        :return: The amount of values.
        """
        return len(self._fetch(_topic))

    def get_sum_of_values(self, _topic, _key):
        """
        Get the sum of values from a topic.

        :param _topic: The topic, e.g. 'nodes'
        :param _key: The key of the values.
        :return: The sum of the values.
        """
        return sum([node[_key] for node in self._fetch(_topic)])

    def _fetch(self, _topic):
        """
        Fetch a topic.

        :param _topic: The topic, e.g. 'nodes'
        :return: The result dictionary.
        """
        if _topic in self.cache:
            return self.cache[_topic]
        else:
            if ':' in self.addr:
                url = 'https://{}/v1/{}'.format(self.addr, _topic)
            else:
                url = 'https://{}:9443/v1/{}'.format(self.addr, _topic)

            rsp = http_get(url, self.username, self.password)
            self.cache[_topic] = rsp
            return rsp
