from ..tools.tools import config_factory
from ..tools.delay import delay_alg
attr_list = [
    [['delay_config', 'function'], 'linear'],
    [['delay_config', 'function'], 'sigmoid'],
    [['delay_config', 'function'], 'constant']
]


def test_delay_alg_random(configure_options):
    def mockreturn():
        return
    config = configure_options(attr_list)
    config['delay_config']['delay'] = 5
    config['delay_config']['min_delay']
    delay_result = delay_alg(3, config['delay_config'])
