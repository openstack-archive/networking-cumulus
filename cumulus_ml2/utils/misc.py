from subprocess import check_output
import yaml

def load_config(path):
    with open(path) as fp:
        return yaml.load(fp)

class Shell(object):
    def __init__(self, root_helper):
        self.root_helper = root_helper

    def call(self, args):
        return check_output([self.root_helper] + args)
