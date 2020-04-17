from jobfunnel.tools.tools import config_factory
from jobfunnel.tools.delay import delay_alg


def mock_rand_uniform(a, b):
    return 5


# test linear, constant and sigmoid delay with random delay off

def test_delay_alg_linear(configure_options, monkeypatch):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'linear'
    delay_result = delay_alg(10, config['delay_config'])
    assert delay_result == [0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.2, 1.4, 1.6, 1.8]


def test_delay_alg_sigmoid(configure_options, monkeypatch):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'sigmoid'
    delay_result = delay_alg(10, config['delay_config'])
    assert delay_result == [0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]


def test_delay_alg_constant(configure_options, monkeypatch):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'constant'
    delay_result = delay_alg(10, config['delay_config'])
    assert delay_result == [0, 8.6, 8.8, 9.0, 9.2, 9.4, 9.6, 9.8, 10.0, 10.0]


# test linear, constant and sigmoid delay with random delay on

def test_delay_alg_linear_random(configure_options, monkeypatch):
    config = configure_options([''])
    config['delay_config']['random'] = True
    config['delay_config']['function'] = 'linear'
    # Fix the value returned random.uniform to a constant
    monkeypatch.setattr('jobfunnel.tools.delay.uniform', mock_rand_uniform)
    delay_result = delay_alg(5, config['delay_config'])
    assert delay_result == [0, 5, 5, 5, 5]


def test_delay_alg_constant_random(configure_options, monkeypatch):
    config = configure_options([''])
    config['delay_config']['random'] = True
    config['delay_config']['function'] = 'constant'
    # Fix the value returned by random.uniform to a constant
    monkeypatch.setattr('jobfunnel.tools.delay.uniform', mock_rand_uniform)
    delay_result = delay_alg(5, config['delay_config'])
    assert delay_result == [0, 5, 5, 5, 5]


def test_delay_alg_sigmoid_random(configure_options, monkeypatch):
    config = configure_options([''])
    config['delay_config']['random'] = True
    config['delay_config']['function'] = 'sigmoid'
    # Fix the value returned by random.uniform to a constant
    monkeypatch.setattr('jobfunnel.tools.delay.uniform', mock_rand_uniform)
    delay_result = delay_alg(5, config['delay_config'])
    assert delay_result == [0, 5, 5, 5, 5]
