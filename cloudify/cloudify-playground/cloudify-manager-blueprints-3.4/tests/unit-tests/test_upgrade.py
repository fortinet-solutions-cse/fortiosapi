import os
import sys
import unittest
import tempfile
from mock import patch

from cloudify.mocks import MockCloudifyContext
sys.path.append(os.path.join(os.path.dirname(__file__),
                             '../../components'))
import utils  # NOQA


TEST_SERVICE_NAME = 'es'
TEST_RESOURCE_NAME = 'test_resource'


class MockNodeProperties(dict):

    def __init__(self, properties):
        self.update(properties)

    def get_all(self):
        return self


def mock_resource_download():
    def download(source):
        resource_base_dir = utils.resource_factory.get_resources_dir(
                TEST_SERVICE_NAME)
        resource_path = os.path.join(resource_base_dir, 'tmp-res-name')
        utils.mkdir(resource_base_dir)
        utils.write_to_json_file('port: 8080', resource_path)
        return resource_path
    return download


def mock_install_ctx():
    install_node_props = {'es_rpm_source_url': 'http://www.mock.com/es.tar.gz',
                          'test_property': 'test'}
    return _create_mock_context(install_node_props)


def _create_mock_context(install_node_props,
                         node_id='es_node',
                         service=TEST_SERVICE_NAME):
    mock_node_props = MockNodeProperties(properties=install_node_props)
    return MockCloudifyContext(node_id=node_id,
                               node_name=service,
                               properties=mock_node_props)


def mock_upgrade_ctx(use_existing_on_upgrade=False):
    upgrade_node_props = \
        {'es_rpm_source_url': 'http://www.mock.com/new-es.tar.gz',
         'use_existing_on_upgrade': use_existing_on_upgrade,
         'test_property': 'new_value',
         'new_property': 'value'}
    return _create_mock_context(upgrade_node_props)


@patch('utils.ctx.download_resource', mock_resource_download())
def _create_resource_file(resource_dest):
    return utils.resource_factory.create(resource_dest,
                                         resource_dest,
                                         TEST_SERVICE_NAME,
                                         user_resource=False,
                                         render=False)


@patch('utils.is_upgrade', False)
@patch('utils.is_rollback', False)
@patch('utils.ctx', mock_install_ctx())
def create_install_resource_file(dest):
    return _create_resource_file(dest)


@patch('utils.is_upgrade', True)
@patch('utils.is_rollback', False)
@patch('utils.ctx', mock_upgrade_ctx())
def create_upgrade_resource_file(dest):
    return _create_resource_file(dest)


@patch('utils.is_upgrade', False)
@patch('utils.is_rollback', True)
@patch('utils.ctx', mock_install_ctx())
def rollback_resource_files(dest):
    return _create_resource_file(dest)


@patch('utils.is_upgrade', False)
@patch('utils.is_rollback', False)
@patch('utils.ctx', mock_install_ctx())
def create_install_props_file(service_name):
    return _create_ctx_props_file(service_name)


@patch('utils.is_upgrade', False)
@patch('utils.is_rollback', True)
@patch('utils.ctx', mock_install_ctx())
def create_rollback_props_file(service_name):
    return _create_ctx_props_file(service_name)


@patch('utils.is_upgrade', True)
@patch('utils.is_rollback', False)
@patch('utils.ctx', mock_upgrade_ctx())
def create_upgrade_props_file(service_name):
    create_install_props_file(service_name)
    return _create_ctx_props_file(service_name)


@patch('utils.is_upgrade', True)
@patch('utils.is_rollback', False)
@patch('utils.ctx', mock_upgrade_ctx(use_existing_on_upgrade=True))
def create_upgrade_props_file_use_existing(service_name):
    create_install_props_file(service_name)
    return _create_ctx_props_file(service_name)


def _create_ctx_props_file(service_name):
    props_file_path = utils.ctx_factory._get_props_file_path(service_name)
    ctx_properties = utils.ctx_factory.create(service_name)
    return ctx_properties, props_file_path


class TestUpgrade(unittest.TestCase):

    def setUp(self):
        super(TestUpgrade, self).setUp()
        self.props_patcher = patch('utils.ctx_factory.BASE_PROPERTIES_PATH',
                                   tempfile.mkdtemp())
        self.res_patcher = patch('utils.BlueprintResourceFactory.'
                                 'BASE_RESOURCES_PATH', tempfile.mkdtemp())
        self.mock_props_path = self.props_patcher.start()
        self.mock_res_path = self.res_patcher.start()

    def test_ctx_prop_install_file_create(self):
        ctx_props, props_file_path = create_install_props_file(
                TEST_SERVICE_NAME)
        self.assertTrue(os.path.isfile(props_file_path))
        props = utils.ctx_factory.get(TEST_SERVICE_NAME)
        self.assertEquals(props.get('test_property'), 'test')
        self.assertDictEqual(props, ctx_props)

    def test_ctx_prop_upgrade_file_create(self):
        ctx_props, upgrade_props_path = create_upgrade_props_file(
                TEST_SERVICE_NAME)
        self.assertIn('new_property', ctx_props.keys())
        self.assertTrue(os.path.isfile(upgrade_props_path))
        props = utils.ctx_factory.get(TEST_SERVICE_NAME)
        self.assertIn('new_property', props.keys())
        self.assertDictEqual(props, ctx_props)

    def test_use_existing_on_upgrade(self):
        ctx_props, _ = create_upgrade_props_file_use_existing(
                TEST_SERVICE_NAME)
        # Assert same value used for upgrade
        self.assertEqual(ctx_props['test_property'], 'test')
        # Assert new property merged with old properties
        self.assertEqual(ctx_props['new_property'], 'value')
        self._assert_rpm_url_overridden(ctx_props)

    def test_new_props_on_upgrade(self):
        ctx_props, _ = create_upgrade_props_file(TEST_SERVICE_NAME)
        self.assertEqual(ctx_props['test_property'], 'new_value')
        self._assert_rpm_url_overridden(ctx_props)

    def _assert_rpm_url_overridden(self, ctx_properties):
        self.assertEqual(ctx_properties['es_rpm_source_url'],
                         'http://www.mock.com/new-es.tar.gz')

    def test_archive_properties(self):
        _, install_path = create_install_props_file(TEST_SERVICE_NAME)
        _, upgrade_path = create_upgrade_props_file(TEST_SERVICE_NAME)

        install_props = \
            utils.ctx_factory.load_rollback_props(TEST_SERVICE_NAME)

        upgrade_props = utils.ctx_factory.get(TEST_SERVICE_NAME)
        self.assertNotEqual(upgrade_props['es_rpm_source_url'],
                            install_props['es_rpm_source_url'])

    def test_restore_properties(self):
        _, install_path = create_install_props_file(TEST_SERVICE_NAME)
        install_props = utils.ctx_factory.get(TEST_SERVICE_NAME)
        _, upgrade_path = create_upgrade_props_file(TEST_SERVICE_NAME)
        upgrade_props = utils.ctx_factory.get(TEST_SERVICE_NAME)
        _, rollback_path = create_rollback_props_file(TEST_SERVICE_NAME)
        rollback_props = utils.ctx_factory.get(TEST_SERVICE_NAME)

        self.assertNotEqual(upgrade_props['es_rpm_source_url'],
                            install_props['es_rpm_source_url'])
        self.assertEqual(install_props['es_rpm_source_url'],
                         rollback_props['es_rpm_source_url'])

    def test_resource_file_create_on_install(self):
        resource_file_dest = '/opt/manager/{0}'.format(TEST_RESOURCE_NAME)
        install_res_file, _ = create_install_resource_file(resource_file_dest)
        resource_json = utils.resource_factory._get_resources_json(
                TEST_SERVICE_NAME)

        # assert resource json contains mapping to the new resource dest
        self.assertEqual(resource_json.get(TEST_RESOURCE_NAME),
                         resource_file_dest)
        self.assertTrue(os.path.isfile(install_res_file))

    def test_resource_file_create_on_update(self):
        resource_file_dest = '/opt/manager/{0}'.format(TEST_RESOURCE_NAME)
        create_upgrade_resource_file(resource_file_dest)
        resource_json = utils.resource_factory._get_resources_json(
                TEST_SERVICE_NAME)

        # assert the upgrade json contains the new resource and its dest
        self.assertEqual(resource_json.get(TEST_RESOURCE_NAME),
                         resource_file_dest)

    def test_archive_resources(self):
        install_resource_dest = '/opt/manager/{0}'.format('install.conf')
        old_resource_path, _ = \
            create_install_resource_file(install_resource_dest)
        # assert install resource created
        self.assertTrue(os.path.isfile(old_resource_path))

        upgrade_resource_dest = '/opt/manager/{0}'.format('upgrade.conf')
        new_resource_path, _ = \
            create_upgrade_resource_file(upgrade_resource_dest)
        # assert upgrade resource created
        self.assertTrue(os.path.isfile(new_resource_path))
        # assert install resource removed
        self.assertFalse(os.path.isfile(old_resource_path))

        # assert resource json was archived
        archived_resource_file = os.path.join(
                utils.resource_factory.get_rollback_resources_dir(
                        TEST_SERVICE_NAME), 'install.conf')
        # assert install resource was archived
        self.assertTrue(os.path.isfile(archived_resource_file))

        # assert resource json values are valid
        rollback_res_json = utils.resource_factory.\
            _get_rollback_resources_json(TEST_SERVICE_NAME)
        self.assertIn('install.conf', rollback_res_json.keys())
        self.assertEqual(install_resource_dest,
                         rollback_res_json.get('install.conf'))

        # assert new resource json exists
        curr_resources_json = os.path.join(
                utils.resource_factory.get_resources_dir(TEST_SERVICE_NAME),
                utils.resource_factory.RESOURCES_JSON_FILE)
        self.assertTrue(os.path.isfile(curr_resources_json))

    @patch('utils.resource_factory._restore_service_configuration',
           lambda x, y: None)
    def test_restore_resources(self):
        install_resource_dest = '/opt/manager/{0}'.format('install.conf')
        install_resource_file, _ = \
            create_install_resource_file(install_resource_dest)
        # assert install file created
        self.assertTrue(os.path.isfile(install_resource_file))
        upgrade_resource_dest = '/opt/manager/{0}'.format('upgrade.conf')
        upgrade_resource_file, _ = \
            create_upgrade_resource_file(upgrade_resource_dest)
        # assert install file moved
        self.assertFalse(os.path.isfile(install_resource_file))
        # assert upgrade file created
        self.assertTrue(os.path.isfile(upgrade_resource_file))
        # rollback resources
        rollback_resource_files(install_resource_dest)

        # assert upgrade resource was removed
        self.assertFalse(os.path.isfile(upgrade_resource_file))
        # assert install resource has been rolled back
        self.assertTrue(os.path.isfile(install_resource_file))
