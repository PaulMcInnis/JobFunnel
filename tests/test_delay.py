import pytest
from jobfunnel.tools.tools import config_factory
from jobfunnel.tools.delay import delay_alg

linear_delay = [0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8]
sigmoid_delay = [0, 0.263, 0.284, 0.307,
                 0.332, 0.358, 0.386, 0.417, 0.449, 0.485]
constant_delay = [0, 8.6, 8.8, 9.0, 9.2, 9.4, 9.6, 9.8, 10.0, 10.0]
random_delay = [0, 5, 5, 5, 5, 5, 5, 5, 5, 5]


# mock random.uniform to get constant values

def mock_rand_uniform(a, b):
    return 5


# test linear, constant and sigmoid delay a min_delay greater than the delay

def test_delay_alg_linear_min_delay_greater_than_delay(configure_options):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'linear'
    # Set the delay value to its default
    config['delay_config']['delay'] = 10
    config['delay_config']['min_delay'] = 15
    delay_result = delay_alg(10, config['delay_config'])
    assert delay_result == linear_delay


def test_delay_alg_sigmoid_min_delay_greater_than_delay(configure_options):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'sigmoid'
    # Set the delay value to its default
    config['delay_config']['delay'] = 10
    config['delay_config']['min_delay'] = 15
    delay_result = delay_alg(10, config['delay_config'])
    assert delay_result == sigmoid_delay


def test_delay_alg_constant_min_delay_greater_than_delay(configure_options):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'constant'
    # Set the delay value to its default
    config['delay_config']['delay'] = 10
    config['delay_config']['min_delay'] = 15
    delay_result = delay_alg(10, config['delay_config'])
    assert delay_result == constant_delay


# test linear, constant and sigmoid delay with negative delay

def test_delay_alg_linear_negative_delay(configure_options):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'linear'
    config['delay_config']['min_delay'] = 0
    config['delay_config']['delay'] = -2
    with pytest.raises(ValueError) as e:
        delay_result = delay_alg(10, config['delay_config'])
    assert str(
        e.value) == "\nYour delay is set to 0 or less.\nCancelling execution..."


def test_delay_alg_sigmoid_negative_delay(configure_options):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'sigmoid'
    config['delay_config']['min_delay'] = 0
    config['delay_config']['delay'] = -2
    with pytest.raises(ValueError) as e:
        delay_result = delay_alg(10, config['delay_config'])
    assert str(
        e.value) == "\nYour delay is set to 0 or less.\nCancelling execution..."


def test_delay_alg_constant_negative_delay(configure_options):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'constant'
    config['delay_config']['min_delay'] = 0
    config['delay_config']['delay'] = -2
    with pytest.raises(ValueError) as e:
        delay_result = delay_alg(10, config['delay_config'])
    assert str(
        e.value) == "\nYour delay is set to 0 or less.\nCancelling execution..."


# test linear, constant and sigmoid delay with a negative min_delay

def test_delay_alg_linear_negative_min_delay(configure_options):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'linear'
    config['delay_config']['min_delay'] = -2
    delay_result = delay_alg(10, config['delay_config'])
    assert delay_result == linear_delay


def test_delay_alg_sigmoid_negative_min_delay(configure_options):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'sigmoid'
    config['delay_config']['min_delay'] = -2
    delay_result = delay_alg(10, config['delay_config'])
    assert delay_result == sigmoid_delay


def test_delay_alg_constant_negative_min_delay(configure_options):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'constant'
    config['delay_config']['min_delay'] = -2
    delay_result = delay_alg(10, config['delay_config'])
    assert delay_result == constant_delay


# test linear, constant and sigmoid delay with random delay off

def test_delay_alg_linear(configure_options):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'linear'
    config['delay_config']['min_delay'] = 0
    delay_result = delay_alg(10, config['delay_config'])
    assert delay_result == linear_delay


def test_delay_alg_sigmoid(configure_options):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'sigmoid'
    config['delay_config']['min_delay'] = 0
    delay_result = delay_alg(10, config['delay_config'])
    assert delay_result == sigmoid_delay


def test_delay_alg_constant(configure_options):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'constant'
    config['delay_config']['min_delay'] = 0
    delay_result = delay_alg(10, config['delay_config'])
    assert delay_result == constant_delay


# test linear, constant and sigmoid delay with random delay off and a list as input

def test_delay_alg_list_linear(configure_options):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'linear'
    config['delay_config']['min_delay'] = 0
    delay_result = delay_alg(['job1', 'job2', 'job3', 'job4', 'job5',
                              'job6', 'job7', 'job8', 'job9', 'job10'], config['delay_config'])
    assert delay_result == linear_delay


def test_delay_alg_list_sigmoid(configure_options):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'sigmoid'
    config['delay_config']['min_delay'] = 0
    delay_result = delay_alg(['job1', 'job2', 'job3', 'job4', 'job5',
                              'job6', 'job7', 'job8', 'job9', 'job10'], config['delay_config'])
    assert delay_result == sigmoid_delay


def test_delay_alg_list_constant(configure_options):
    config = configure_options([''])
    config['delay_config']['random'] = False
    config['delay_config']['function'] = 'constant'
    config['delay_config']['min_delay'] = 0
    delay_result = delay_alg(['job1', 'job2', 'job3', 'job4', 'job5',
                              'job6', 'job7', 'job8', 'job9', 'job10'], config['delay_config'])
    assert delay_result == constant_delay


# test linear, constant and sigmoid delay with random delay on

def test_delay_alg_linear_random(configure_options, monkeypatch):
    config = configure_options([''])
    config['delay_config']['random'] = True
    config['delay_config']['function'] = 'linear'
    # Fix the value returned random.uniform to a constant
    monkeypatch.setattr('jobfunnel.tools.delay.uniform', mock_rand_uniform)
    delay_result = delay_alg(10, config['delay_config'])
    assert delay_result == random_delay


def test_delay_alg_constant_random(configure_options, monkeypatch):
    config = configure_options([''])
    config['delay_config']['random'] = True
    config['delay_config']['function'] = 'constant'
    # Fix the value returned by random.uniform to a constant
    monkeypatch.setattr('jobfunnel.tools.delay.uniform', mock_rand_uniform)
    delay_result = delay_alg(10, config['delay_config'])
    assert delay_result == random_delay


def test_delay_alg_sigmoid_random(configure_options, monkeypatch):
    config = configure_options([''])
    config['delay_config']['random'] = True
    config['delay_config']['function'] = 'sigmoid'
    monkeypatch.setattr('jobfunnel.tools.delay.uniform', mock_rand_uniform)
    delay_result = delay_alg(10, config['delay_config'])
    assert delay_result == random_delay
