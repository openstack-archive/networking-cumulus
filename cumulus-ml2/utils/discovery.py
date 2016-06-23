class DiscoveryError(RuntimeError):
    pass

class DiscoveryManager(object):
    def __init__(self, shell):
        self.shell = shell

    def find_interface(self, hostname):
        neighbors = self.fetch_neighbors()

        for interface, details in neighbors.iteritems():
            if details['chassis']['name'] == hostname:
                return interface
        # This causes a problem where neutron asks for serverX port
        # but it doesn't exist. If in a multi-VM bringup, causes neutron
        # to go nuts so for now just don't do it. If user actually forgot
        # to enable LLDP on server port. Then, too bad. it never gets provisioned
        # Better way to handle this problem will be investigated. For now, always
        # remember to configure LLDP correctly. Suggest even have PTM running
        # to ensure LLDP is configured correctly
        # raise DiscoveryError('Could not find host: {}'.format(hostname))

    def find_neighbor_for_interface(self, interface):
        neighbors = self.fetch_neighbors()

        try:
            return neighbors[interface]['chassis']
        except KeyError:
            pass

    def fetch_neighbors(self):
        output = self.shell.call(['lldpcli', 'show', 'neighbors', '-f', 'keyvalue'])
        parsed = parse_lldpd_output(output)

        return parsed['lldp']

def parse_lldpd_output(output):
    """
    http://stackoverflow.com/questions/20577303/parse-lldp-output-with-python
    """
    result = {}
    entries = output.strip().split('\n')

    for entry in entries:
        path, value = entry.strip().split('=', 1)
        path = path.split('.')
        components, final = path[:-1], path[-1]

        current = result
        for component in components:
            current = current.setdefault(component, {})
        current[final] = value

    return result
