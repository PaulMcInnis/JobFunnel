import pytest
from jobfunnel.tools.tools import config_factory
from jobfunnel.tools.delay import delay_alg

# Define mock data for this test module

linear_delay = [0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8]
sigmoid_delay = [0, 0.263, 0.284, 0.307,
                 0.332, 0.358, 0.386, 0.417, 0.449, 0.485]
constant_delay = [0, 8.6, 8.8, 9.0, 9.2, 9.4, 9.6, 9.8, 10.0, 10.0]
random_delay = [0, 5, 5, 5, 5, 5, 5, 5, 5, 5]
job_list = ['job1', 'job2', 'job3', 'job4', 'job5',
            'job6', 'job7', 'job8', 'job9', 'job10']


# mock random.uniform to get constant values


def mock_rand_uniform(a, b):
    return 5


@pytest.mark.parametrize('function, expected_result', [('linear', linear_delay), ('sigmoid', sigmoid_delay), ('constant', constant_delay)])
class TestClass:

    # test linear, constant and sigmoid delay
    # This test considers configurations with random and converge fields
    @pytest.mark.parametrize('random,converge', [(True, True), (True, False), (False, False)])
    def test_delay_alg(self, configure_options, function, expected_result, random, converge, monkeypatch):
        config = configure_options([''])
        config['delay_config']['random'] = random
        config['delay_config']['function'] = function
        config['delay_config']['converge'] = converge
        if random:
            monkeypatch.setattr(
                'jobfunnel.tools.delay.uniform', mock_rand_uniform)
            expected_result = random_delay
        else:
            config['delay_config']['min_delay'] = 0
        delay_result = delay_alg(10, config['delay_config'])
        assert delay_result == expected_result

    # test linear, constant and sigmoid delay with a negative min_delay

    def test_delay_alg_negative_min_delay(self, configure_options, function, expected_result):
        config = configure_options([''])
        config['delay_config']['random'] = False
        config['delay_config']['function'] = function
        config['delay_config']['min_delay'] = -2
        delay_result = delay_alg(10, config['delay_config'])
        assert delay_result == expected_result

    # test linear, constant and sigmoid delay when min_delay is greater than the delay

    def test_delay_alg_min_delay_greater_than_delay(self, configure_options, function, expected_result):
        config = configure_options([''])
        config['delay_config']['random'] = False
        config['delay_config']['function'] = function
        # Set the delay value to its default
        config['delay_config']['delay'] = 10
        config['delay_config']['min_delay'] = 15
        delay_result = delay_alg(10, config['delay_config'])
        assert delay_result == expected_result

    # test linear, constant and sigmoid delay with negative delay

    def test_delay_alg_negative_delay(self, configure_options, function, expected_result):
        config = configure_options([''])
        config['delay_config']['random'] = False
        config['delay_config']['function'] = function
        config['delay_config']['min_delay'] = 0
        config['delay_config']['delay'] = -2
        with pytest.raises(ValueError) as e:
            delay_result = delay_alg(10, config['delay_config'])
        assert str(
            e.value) == "\nYour delay is set to 0 or less.\nCancelling execution..."

    # test linear, constant and sigmoid delay with random and a list as input

    def test_delay_alg_list_linear(self, configure_options, function, expected_result):
        config = configure_options([''])
        config['delay_config']['random'] = False
        config['delay_config']['function'] = function
        config['delay_config']['min_delay'] = 0
        delay_result = delay_alg(job_list, config['delay_config'])
        assert delay_result == expected_result
