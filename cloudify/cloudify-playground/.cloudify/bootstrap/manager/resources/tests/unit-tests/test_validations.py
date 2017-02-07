import os
import imp
import sys

import testtools
from mock import patch

from test_upgrade import _create_mock_context


validate = imp.load_source(
    'validate', os.path.join(
        os.path.dirname(__file__),
        '../../components/manager/scripts/validate.py'))


os_distro = ('distro', '1')


class TestValidations(testtools.TestCase):
    node_properties = {
        'ignore_bootstrap_validations': False,
        'es_heap_size': '2g',
        'manager_resources_package': 'http://non-existing-domain.com/package',
        'minimum_required_total_physical_memory_in_mb': 3792,
        'minimum_required_available_disk_space_in_gb': 5,
        'allowed_heap_size_gap_in_mb': 1024
    }
    CTX = _create_mock_context(node_properties, node_id='node', service='test')
    node_properties.update({'ignore_bootstrap_validations': 'True'})
    IGNORE_VALIDATIONS_CTX = _create_mock_context(
        node_properties, node_id='_node', service='test')

    @patch('validate.ctx', CTX)
    @patch('validate._get_os_distro', return_value=('redhat', '7'))
    @patch('validate._get_host_total_memory', return_value=100000000)
    @patch('validate._get_available_host_disk_space', return_value=100)
    @patch('validate._validate_resources_package_url', return_value=None)
    def test_successful_validation(self, *_):
        validate.validate()

    @patch('validate.ctx', IGNORE_VALIDATIONS_CTX)
    @patch('validate._get_os_distro', return_value=os_distro)
    @patch('validate._get_host_total_memory', return_value=1)
    @patch('validate._get_available_host_disk_space', return_value=1)
    @patch('validate._validate_resources_package_url', return_value=None)
    @patch('validate._get_python_version', return_value=(8, 8))
    def test_failed_yet_ignored_validation(self, *_):
        validate.validate()

    @patch('validate.ctx', CTX)
    @patch('validate._get_os_distro', return_value=os_distro)
    @patch('validate._get_host_total_memory', return_value=1)
    @patch('validate._get_available_host_disk_space', return_value=1)
    def test_failed_validation(self, *_):
        validate.ctx.abort_operation = lambda message: sys.exit(message)
        ex = self.assertRaises(SystemExit, validate.validate)
        self.assertIn(
            validate._error('Cloudify Manager requires'),
            str(ex))
        self.assertIn(
            validate._error('The provided host does not have enough memory'),
            str(ex))
        self.assertIn(
            validate._error('The provided host does not have enough disk'),
            str(ex))
        self.assertIn(
            validate._error('The heapsize provided for Elasticsearch'),
            str(ex))
        self.assertIn(
            validate._error(
                "The Manager's Resources Package "
                "http://non-existing-domain.com/package"),
            str(ex))

    def test_fail_validate_resources_package_url(self):
        test_url = 'http://non-existent-domain.com/non-existent-file.tar.gz'
        error = validate._validate_resources_package_url(test_url)
        desired_error = (validate._error(
            "The Manager's Resources Package {0} is not accessible "
            "(HTTP Error: {1})".format(test_url, '404')))
        self.assertEqual(desired_error, error)

    @patch('validate.ctx', CTX)
    @patch('validate._get_os_distro', return_value=os_distro)
    def test_validate_supported_distros_ok(self, _):
        error = validate._validate_supported_distros(['distro'], ['1'])
        self.assertIsNone(error)

    @patch('validate.ctx', CTX)
    @patch('validate._get_os_distro', return_value=os_distro)
    def _test_fail_validate_supported_distros(self, _, distros, versions):
        current_distro, current_version = validate._get_os_distro()
        error = validate._validate_supported_distros(distros, versions)
        desired_error = 'Manager requires either '
        self.assertIn(desired_error, error)

    def test_fail_validate_supported_distros_bad_distro(self):
        self._test_fail_validate_supported_distros(['bla'], ['1'])

    def test_fail_validate_supported_distros_bad_version(self):
        self._test_fail_validate_supported_distros(['distro'], ['2'])

    def test_fail_validate_supported_distros_bad_version_and_distro(self):
        self._test_fail_validate_supported_distros(['bla'], ['2'])

    @patch('validate.ctx', CTX)
    @patch('validate._get_host_total_memory', return_value=1023)
    def test_fail_validate_physical_memory(self, _):
        error = validate._validate_sufficient_memory(1024)
        desired_error = validate._error(
            'The provided host does not have enough memory')
        self.assertIn(desired_error, error)

    @patch('validate.ctx', CTX)
    @patch('validate._get_host_total_memory', return_value=1024)
    def test_validate_edgy_physical_memory(self, _):
        error = validate._validate_sufficient_memory(1024)
        self.assertIsNone(error)

    @patch('validate.ctx', CTX)
    def test_validate_physical_memory(self):
        error = validate._validate_sufficient_memory(1)
        self.assertIsNone(error)

    @patch('validate.ctx', CTX)
    @patch('validate._get_available_host_disk_space', return_value=1)
    def test_fail_validate_available_disk_space(self, _):
        error = validate._validate_sufficient_disk_space(2)
        desired_error = validate._error(
            'The provided host does not have enough disk space')
        self.assertIn(desired_error, error)

    @patch('validate.ctx', CTX)
    def test_validate_available_disk_space(self):
        error = validate._validate_sufficient_disk_space(1)
        self.assertIsNone(error)

    @patch('validate.ctx', CTX)
    @patch('validate._get_host_total_memory', return_value=100)
    def test_fail_validate_es_heap_size_large_gap(self, _):
        error = validate._validate_es_heap_size('90m', 11)
        desired_error = validate._error(
            'The heapsize provided for Elasticsearch')
        self.assertIn(desired_error, error)

    @patch('validate.ctx', CTX)
    @patch('validate._get_host_total_memory', return_value=100)
    def test_fail_validate_es_heap_size(self, _):
        error = validate._validate_es_heap_size('101m', 1)
        desired_error = validate._error(
            'The heapsize provided for Elasticsearch')
        self.assertIn(desired_error, error)

    @patch('validate.ctx', CTX)
    def test_validate_es_heap_size(self):
        error = validate._validate_es_heap_size('512m', 512)
        self.assertIsNone(error)

    @patch('validate.ctx', CTX)
    @patch('validate._get_python_version', return_value=(2, 7))
    def test_validate_python_version(self, _):
        error = validate._validate_python_version(2, 7)
        self.assertIsNone(error)

    @patch('validate.ctx', CTX)
    @patch('validate._get_python_version', return_value=(2, 7))
    def test_fail_validate_unacceptable_python_major_version(self, _):
        error = validate._validate_python_version(2, 0)
        self.assertIn('You must be running Python', error)

    @patch('validate.ctx', CTX)
    @patch('validate._get_python_version', return_value=(2, 7))
    def test_fail_validate_unacceptable_python_minor_version(self, _):
        error = validate._validate_python_version(3, 7)
        self.assertIn('You must be running Python', error)

    def test_get_python_version(self):
        major = sys.version_info[0]
        minor = sys.version_info[1]
        version = validate._get_python_version()
        self.assertEqual(version[0], major)
        self.assertEqual(version[1], minor)
