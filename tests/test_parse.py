"""Test CLI parsing
"""
import pytest
from jobfunnel.config import parse_cli, config_builder
from jobfunnel.resources.defaults import *

# FIXME
# @pytest.mark.parametrize("kwargs, exception, match", [
#     (
#         {
#             'settings_yaml_file': 'demo/settings.yaml',
#         },
#         ValueError,
#         r".*If specifying paths you must pass all arguments.*",
#     ),

# ])
# def test_config_builder(mocker, kwargs, exception, match):

#     # Inject our settings as augmentations of CLI
#     # TODO: we should break parse_cli into own test
#     args = vars(parse_cli())
#     for kwarg, value in kwargs.items():
#         args[kwarg] = value

#     patch_os = mocker.patch('jobfunnel.config.cli.os')
#     mocker.patch('jobfunnel.config.cli.vars', return_value=args)

#     # FUT
#     if exception:
#         with pytest.raises(exception, match=match):
#             config_builder(None)
#     else:
#         cfg = config_builder(None)
