import os
import tempfile
from unittest.mock import patch, MagicMock
from django.test import TestCase
from core.github.data_source_handler import read_repository
from core.utils import get_default_settings

class TestReadRepository(TestCase):
    @classmethod
    def setUpClass(cls):
        get_default_settings()
        super().setUpClass()
        # Create mock settings that will be used across all tests
        cls.mock_settings = MagicMock()
        cls.mock_settings.package_manifest_files = [
            'requirements.txt',
            'setup.py',
            'package.json',
            'Gemfile',
            'pom.xml'
        ]
        cls.mock_settings.code_file_extensions = [
            '.py',
            '.js',
            '.ts',
            '.java',
            '.rb',
            '.txt'
        ]
        # Start the patcher
        cls.settings_patcher = patch('core.github.data_source_handler.get_default_settings', 
                                   return_value=cls.mock_settings)
        cls.settings_patcher.start()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Stop the patcher
        cls.settings_patcher.stop()

    def setUp(self):
        # Create a temporary directory structure for testing
        self.temp_dir = tempfile.mkdtemp()
        
        # Create some test files
        self.create_test_files()
        
    def tearDown(self):
        # Clean up the temporary directory
        os.system(f"rm -rf {self.temp_dir}")
        
    def create_test_files(self):
        """Create a test file structure for testing"""
        # Create test files with different extensions
        files = {
            'main.py': 'print("Hello")',
            'test_main.py': 'def test_hello(): pass',
            'src/api.py': 'def api(): pass',
            'src/utils.js': 'function util() {}',
            'src/utils/helper.py': 'def helper(): pass',
            'src/types.ts': 'interface Type {}',
            'docs/readme.md': '# README',
            'requirements.txt': 'django==3.2',
            '.env': 'SECRET=123',
            'node_modules/package/index.js': 'module.exports = {}',
            # Additional test files for glob pattern testing
            'file1.txt': 'test1',
            'fileA.txt': 'testA',
            'file12.txt': 'test12',
            'subdir/main.py': 'print("subdir")',
            'a/b/c/script.py': 'print("deep")',
            'tests/test_math.py': 'def test_math(): pass',
            'src/test_utils.py': 'def test_utils(): pass',
            'src/level1/file.py': 'print("level1")',
            'src/level2/file.py': 'print("level2")',
        }
        
        for path, content in files.items():
            full_path = os.path.join(self.temp_dir, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)

        # Create empty directories for directory matching tests
        empty_dirs = ['empty_subdir', 'empty_tests']
        for dir_name in empty_dirs:
            os.makedirs(os.path.join(self.temp_dir, dir_name), exist_ok=True)

    def test_basic_repository_reading(self):
        """Test basic repository reading without glob patterns"""
        structure = read_repository(self.temp_dir)
        
        # Should include code files and package manifests
        paths = [item['path'] for item in structure]
        
        self.assertIn('main.py', paths)
        self.assertIn('test_main.py', paths)
        self.assertIn('src/api.py', paths)
        self.assertIn('src/utils.js', paths)
        self.assertIn('src/types.ts', paths)
        self.assertIn('requirements.txt', paths)
        
        # Should not include non-code files or excluded directories
        self.assertNotIn('docs/readme.md', paths)
        self.assertNotIn('.env', paths)
        self.assertNotIn('node_modules/package/index.js', paths)

    def test_include_python_files_only(self):
        """Test including only Python files using glob pattern"""
        structure = read_repository(
            self.temp_dir,
            include=True,
            glob_pattern="**/*.py"
        )
        
        paths = [item['path'] for item in structure]
        
        # Should only include Python files
        self.assertIn('main.py', paths)
        self.assertIn('test_main.py', paths)
        self.assertIn('src/api.py', paths)
        
        # Should not include non-Python files
        self.assertNotIn('src/utils.js', paths)
        self.assertNotIn('src/types.ts', paths)
        self.assertNotIn('requirements.txt', paths)

    def test_exclude_test_files(self):
        """Test excluding test files using glob pattern"""
        structure = read_repository(
            self.temp_dir,
            include=False,
            glob_pattern="test_*.py"
        )
        
        paths = [item['path'] for item in structure]
        
        # Should not include test files
        self.assertNotIn('test_main.py', paths)
        
        # Should include non-test files
        self.assertIn('main.py', paths)
        self.assertIn('src/api.py', paths)
        self.assertIn('src/utils.js', paths)

    def test_include_src_directory_only(self):
        """Test including only files in src directory"""
        structure = read_repository(
            self.temp_dir,
            include=True,
            glob_pattern="src/**/*"
        )
        
        paths = [item['path'] for item in structure]
        
        # Should only include files from src directory
        self.assertIn('src/api.py', paths)
        self.assertIn('src/utils.js', paths)
        self.assertIn('src/types.ts', paths)
        
        # Should not include files outside src
        self.assertNotIn('main.py', paths)
        self.assertNotIn('test_main.py', paths)
        self.assertNotIn('requirements.txt', paths)

    def test_empty_glob_pattern(self):
        """Test that empty glob pattern doesn't affect filtering"""
        structure1 = read_repository(self.temp_dir)
        structure2 = read_repository(self.temp_dir, glob_pattern="")
        structure3 = read_repository(self.temp_dir, glob_pattern=None)
        
        # All three calls should return the same structure
        self.assertEqual(
            [item['path'] for item in structure1],
            [item['path'] for item in structure2]
        )
        self.assertEqual(
            [item['path'] for item in structure2],
            [item['path'] for item in structure3]
        )

    def test_large_file_exclusion(self):
        """Test that files larger than 10MB are excluded"""
        # Create a large test file (11MB)
        large_file_path = os.path.join(self.temp_dir, 'large.py')
        with open(large_file_path, 'wb') as f:
            f.write(b'0' * (11 * 1024 * 1024))
            
        structure = read_repository(self.temp_dir)
        paths = [item['path'] for item in structure]
        
        # Large file should be excluded
        self.assertNotIn('large.py', paths)

    def test_multiple_extensions(self):
        """Test glob pattern with multiple extensions"""
        structure = read_repository(
            self.temp_dir,
            include=True,
            glob_pattern="**/*.{js,ts}"
        )
        
        paths = [item['path'] for item in structure]
        
        # Should include both JS and TS files
        self.assertIn('src/utils.js', paths)
        self.assertIn('src/types.ts', paths)
        
        # Should not include other files
        self.assertNotIn('main.py', paths)
        self.assertNotIn('requirements.txt', paths)

    def test_basic_matching(self):
        """Test basic matching with *.py pattern"""
        structure = read_repository(
            self.temp_dir,
            include=True,
            glob_pattern="*.py"
        )
        
        paths = [item['path'] for item in structure]
        
        # Should match Python files in current dir only
        self.assertIn('main.py', paths)
        self.assertIn('test_main.py', paths)
        
        # Should not match Python files in subdirectories
        self.assertNotIn('src/api.py', paths)
        self.assertNotIn('subdir/main.py', paths)

    def test_recursive_matching(self):
        """Test recursive matching with **/*.py pattern"""
        structure = read_repository(
            self.temp_dir,
            include=True,
            glob_pattern="**/*.py"
        )
        
        paths = [item['path'] for item in structure]
        
        # Should match Python files in all directories
        self.assertIn('main.py', paths)
        self.assertIn('src/api.py', paths)
        self.assertIn('subdir/main.py', paths)
        self.assertIn('a/b/c/script.py', paths)

    def test_recursive_test_files(self):
        """Test recursive matching of test files with **/test_*.py pattern"""
        structure = read_repository(
            self.temp_dir,
            include=True,
            glob_pattern="**/test_*.py"
        )
        
        paths = [item['path'] for item in structure]
        
        # Should match test files in any directory
        self.assertIn('test_main.py', paths)
        self.assertIn('tests/test_math.py', paths)
        self.assertIn('src/test_utils.py', paths)
        
        # Should not match non-test Python files
        self.assertNotIn('main.py', paths)
        self.assertNotIn('src/api.py', paths)

    def test_character_matching(self):
        """Test character wildcard and character class matching"""
        # Test single character wildcard
        structure1 = read_repository(
            self.temp_dir,
            include=True,
            glob_pattern="file?.txt"
        )
        paths1 = [item['path'] for item in structure1]
        
        self.assertIn('file1.txt', paths1)
        self.assertIn('fileA.txt', paths1)
        self.assertNotIn('file12.txt', paths1)
        
        # Test character class
        structure2 = read_repository(
            self.temp_dir,
            include=True,
            glob_pattern="file[0-9].txt"
        )
        paths2 = [item['path'] for item in structure2]
        
        self.assertIn('file1.txt', paths2)
        self.assertNotIn('fileA.txt', paths2)
        self.assertNotIn('file12.txt', paths2)

    def test_mixed_path_matching(self):
        """Test mixed path matching patterns"""
        # Test file in immediate subdir
        structure1 = read_repository(
            self.temp_dir,
            include=True,
            glob_pattern="*/*/file.py"
        )
        paths1 = [item['path'] for item in structure1]
        
        self.assertIn('src/level1/file.py', paths1)
        self.assertIn('src/level2/file.py', paths1)

    def test_no_match(self):
        """Test pattern with no matches"""
        structure = read_repository(
            self.temp_dir,
            include=True,
            glob_pattern="nope/*.txt"
        )
        
        self.assertEqual(len(structure), 0)
