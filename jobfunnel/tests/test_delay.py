from ..tools.tools import config_factory
from ..tools.delay import delay_alg


def test_delay_alg_linear(configure_options, monkeypatch):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'linear'
    delay_result = delay_alg(10, config['delay_config'])
    assert delay_result == [0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.2, 1.4, 1.6, 1.8]


def test_delay_alg_linear_random(configure_options, monkeypatch):
    config = configure_options([''])

    def mock_rand_uniform(a, b):
        return 5
    config['delay_config']['random'] = True
    config['delay_config']['function'] = 'linear'
    # Fix the value returned random.uniform to a constant
    monkeypatch.setattr('jobfunnel.tools.delay.uniform', mock_rand_uniform)
    delay_result = delay_alg(5, config['delay_config'])
    assert delay_result == [0, 5, 5, 5, 5]


def test_delay_alg_constant_random(configure_options, monkeypatch):
    config = configure_options([''])

    def mock_rand_uniform(a, b):
        return 5
    config['delay_config']['random'] = True
    config['delay_config']['function'] = 'constant'
    # Fix the value returned by random.uniform to a constant
    monkeypatch.setattr('jobfunnel.tools.delay.uniform', mock_rand_uniform)
    delay_result = delay_alg(5, config['delay_config'])
    assert delay_result == [0, 5, 5, 5, 5]


def test_delay_alg_sigmoid_random(configure_options, monkeypatch):
    config = configure_options([''])

    def mock_rand_uniform(a, b):
        return 5
    config['delay_config']['random'] = True
    config['delay_config']['function'] = 'sigmoid'
    # Fix the value returned by random.uniform to a constant
    monkeypatch.setattr('jobfunnel.tools.delay.uniform', mock_rand_uniform)
    delay_result = delay_alg(5, config['delay_config'])
    assert delay_result == [0, 5, 5, 5, 5]
