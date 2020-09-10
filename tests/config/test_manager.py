# FIXME: need to break down config manager testing a bit more
# @pytest.mark.parametrize('pass_del_cfg', (True, False))
# def test_config_manager_init(mocker, pass_del_cfg):
#     """NOTE: unlike other configs this one validates itself on creation
#     """
#     # Mocks
#     patch_del_cfg = mocker.patch('jobfunnel.config.manager.DelayConfig')
#     patch_os = mocker.patch('jobfunnel.config.manager.os')
#     patch_os.path.exists.return_value = False  # check it makes all paths
#     mock_master_csv = mocker.Mock()
#     mock_block_list = mocker.Mock()
#     mock_dupe_list = mocker.Mock()
#     mock_cache_folder = mocker.Mock()
#     mock_search_cfg = mocker.Mock()
#     mock_proxy_cfg = mocker.Mock()
#     mock_del_cfg = mocker.Mock()

#     # FUT
#     cfg = JobFunnelConfigManager(
#         master_csv_file=mock_master_csv,
#         user_block_list_file=mock_block_list,
#         duplicates_list_file=mock_dupe_list,
#         cache_folder=mock_cache_folder,
#         search_config=mock_search_cfg,
#         delay_config=mock_del_cfg if pass_del_cfg else None,
#         proxy_config=mock_proxy_cfg,
#         log_file='', # TODO optional?
#     )

#     # Assertions
