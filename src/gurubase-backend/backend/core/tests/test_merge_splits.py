import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
from django.test import TestCase
from core.utils import get_default_settings
# Add the project root to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestMergeSplits(TestCase):
    def setUp(self):
        # Mock text_embedding and code_embedding used in the merge_splits function
        get_default_settings()
        self.text_embedding_mock = [0.1, 0.2, 0.3]
        self.code_embedding_mock = [0.4, 0.5, 0.6]
        
        # Create a mock MilvusClient instance
        self.milvus_client_mock = MagicMock()
        
        # Patch the MilvusClient import in core.utils
        self.milvus_patcher = patch('core.utils.MilvusClient', return_value=self.milvus_client_mock)
        self.milvus_patcher.start()
        
        # Import function after patching
        from core.utils import merge_splits
        self.merge_splits = merge_splits
    
    def tearDown(self):
        self.milvus_patcher.stop()
    
    def test_single_split(self):
        """Test when there's only a single split in the document"""
        # Setup
        fetched_doc = {
            'entity': {
                'metadata': {'split_num': 1},
                'text': 'This is a single split document.'
            }
        }

        adjacent_result = []
        additional_result = []

        self.milvus_client_mock.search.side_effect = [[adjacent_result], [additional_result]]
        
        # Execute
        result = self.merge_splits(
            self.milvus_client_mock,
            self.text_embedding_mock,
            self.code_embedding_mock,
            fetched_doc,
            'test_collection',
            'link_key',
            'link1',
            code=False,
            merge_limit=4
        )
        
        # Assert
        self.assertEqual(result['entity']['text'], 'This is a single split document.')
        self.assertEqual(self.milvus_client_mock.search.call_count, 2)
    
    def test_fetched_at_end_two_splits(self):
        """Test when fetched split is at the end and doc has 2 splits total"""
        # Setup
        fetched_doc = {
            'entity': {
                'metadata': {'split_num': 2},
                'text': 'This is the second split.'
            }
        }
        
        # Mock the search for adjacent splits
        adjacent_result = [{
            'entity': {
                'metadata': {'split_num': 1},
                'text': 'This is the first split.'
            }
        }]
        self.milvus_client_mock.search.return_value = [adjacent_result]
        
        # Execute
        result = self.merge_splits(
            self.milvus_client_mock,
            self.text_embedding_mock,
            self.code_embedding_mock,
            fetched_doc,
            'test_collection',
            'link_key',
            'link1',
            code=False,
            merge_limit=4
        )
        
        # Assert
        self.assertEqual(result['entity']['text'], 'This is the first split.\nThis is the second split.')
        self.milvus_client_mock.search.assert_called()
    
    def test_fetched_at_end_three_splits(self):
        """Test when fetched split is at the end and doc has 3 splits total"""
        # Setup
        fetched_doc = {
            'entity': {
                'metadata': {'split_num': 3},
                'text': 'This is the third split.'
            }
        }
        
        # Mock the search for adjacent splits
        adjacent_result = [
            {
                'entity': {
                    'metadata': {'split_num': 1},
                    'text': 'This is the first split.'
                }
            },
            {
                'entity': {
                    'metadata': {'split_num': 2},
                    'text': 'This is the second split.'
                }
            }
        ]
        self.milvus_client_mock.search.return_value = [adjacent_result]
        
        # Execute
        result = self.merge_splits(
            self.milvus_client_mock,
            self.text_embedding_mock,
            self.code_embedding_mock,
            fetched_doc,
            'test_collection',
            'link_key',
            'link1',
            code=False,
            merge_limit=4
        )
        
        # Assert
        self.assertEqual(result['entity']['text'], 'This is the first split.\nThis is the second split.\nThis is the third split.')
        self.milvus_client_mock.search.assert_called()
    
    def test_fetched_at_beginning_two_splits(self):
        """Test when fetched split is at the beginning and doc has 2 splits total"""
        # Setup
        fetched_doc = {
            'entity': {
                'metadata': {'split_num': 1},
                'text': 'This is the first split.'
            }
        }
        
        # Mock the search for adjacent splits
        adjacent_result = [{
            'entity': {
                'metadata': {'split_num': 2},
                'text': 'This is the second split.'
            }
        }]
        self.milvus_client_mock.search.return_value = [adjacent_result]
        
        # Execute
        result = self.merge_splits(
            self.milvus_client_mock,
            self.text_embedding_mock,
            self.code_embedding_mock,
            fetched_doc,
            'test_collection',
            'link_key',
            'link1',
            code=False,
            merge_limit=4
        )
        
        # Assert
        self.assertEqual(result['entity']['text'], 'This is the first split.\nThis is the second split.')
        self.milvus_client_mock.search.assert_called()
    
    def test_fetched_at_beginning_three_splits(self):
        """Test when fetched split is at the beginning and doc has 3 splits total"""
        # Setup
        fetched_doc = {
            'entity': {
                'metadata': {'split_num': 1},
                'text': 'This is the first split.'
            }
        }
        
        # Mock the search for adjacent splits
        adjacent_result = [
            {
                'entity': {
                    'metadata': {'split_num': 2},
                    'text': 'This is the second split.'
                }
            },
            {
                'entity': {
                    'metadata': {'split_num': 3},
                    'text': 'This is the third split.'
                }
            }
        ]
        self.milvus_client_mock.search.return_value = [adjacent_result]
        
        # Execute
        result = self.merge_splits(
            self.milvus_client_mock,
            self.text_embedding_mock,
            self.code_embedding_mock,
            fetched_doc,
            'test_collection',
            'link_key',
            'link1',
            code=False,
            merge_limit=4
        )
        
        # Assert
        self.assertEqual(result['entity']['text'], 'This is the first split.\nThis is the second split.\nThis is the third split.')
        self.milvus_client_mock.search.assert_called()
    
    def test_fetched_in_middle(self):
        """Test when fetched split is in the middle and doc has 3 splits total"""
        # Setup
        fetched_doc = {
            'entity': {
                'metadata': {'split_num': 3},
                'text': 'This is the third split.'
            }
        }
        
        # Mock the search for adjacent splits
        adjacent_result = [
            {
                'entity': {
                    'metadata': {'split_num': 1},
                    'text': 'This is the first split.'
                }
            },
            {
                'entity': {
                    'metadata': {'split_num': 2},
                    'text': 'This is the second split.'
                }
            },
            {
                'entity': {
                    'metadata': {'split_num': 4},
                    'text': 'This is the fourth split.'
                }
            },
            {
                'entity': {
                    'metadata': {'split_num': 5},
                    'text': 'This is the fifth split.'
                }
            }
        ]

        additional_result = [
            {
                'entity': {
                    'metadata': {'split_num': 6},
                    'text': 'This is the sixth split.'
                }
            }
        ]

        self.milvus_client_mock.search.side_effect = [[adjacent_result], [additional_result]]
        
        # Execute
        result = self.merge_splits(
            self.milvus_client_mock,
            self.text_embedding_mock,
            self.code_embedding_mock,
            fetched_doc,
            'test_collection',
            'link_key',
            'link1',
            code=False,
            merge_limit=6
        )
        
        # Assert
        self.assertEqual(result['entity']['text'], 'This is the second split.\nThis is the third split.\nThis is the fourth split.\n\n...truncated...\n\nThis is the sixth split.')
        self.assertEqual(self.milvus_client_mock.search.call_count, 2)
    
    def test_less_than_five_splits(self):
        """Test when doc has less than 5 splits - should merge 4 in order"""
        # Setup
        fetched_doc = {
            'entity': {
                'metadata': {'split_num': 2},
                'text': 'This is the second split.'
            }
        }
        
        # First search for adjacent splits
        adjacent_result = [
            {
                'entity': {
                    'metadata': {'split_num': 1},
                    'text': 'This is the first split.'
                }
            },
            {
                'entity': {
                    'metadata': {'split_num': 3},
                    'text': 'This is the third split.'
                }
            }
        ]
        
        # Second search for additional splits
        additional_result = [
            {
                'entity': {
                    'metadata': {'split_num': 4},
                    'text': 'This is the fourth split.'
                }
            }
        ]
        
        # Configure milvus_client_mock to return different values on consecutive calls
        self.milvus_client_mock.search.side_effect = [[adjacent_result], [additional_result]]
        
        # Execute
        result = self.merge_splits(
            self.milvus_client_mock,
            self.text_embedding_mock,
            self.code_embedding_mock,
            fetched_doc,
            'test_collection',
            'link_key',
            'link1',
            code=False,
            merge_limit=6
        )
        
        # Assert
        self.assertEqual(result['entity']['text'], 'This is the first split.\nThis is the second split.\nThis is the third split.\nThis is the fourth split.')
        # Should call search twice: once for adjacent and once for additional
        self.assertEqual(self.milvus_client_mock.search.call_count, 2)
    
    def test_more_than_six_splits_with_truncation(self):
        """Test when doc has more than 6 splits with truncation between non-adjacent splits"""
        # Setup
        fetched_doc = {
            'entity': {
                'metadata': {'split_num': 5},
                'text': 'This is the fifth split.'
            }
        }
        
        # First search for adjacent splits
        adjacent_result = [
            {
                'entity': {
                    'metadata': {'split_num': 3},
                    'text': 'This is the third split.'
                }
            },
            {
                'entity': {
                    'metadata': {'split_num': 4},
                    'text': 'This is the fourth split.'
                }
            },
            {
                'entity': {
                    'metadata': {'split_num': 6},
                    'text': 'This is the sixth split.'
                }
            },
            {
                'entity': {
                    'metadata': {'split_num': 7},
                    'text': 'This is the seventh split.'
                }
            }
        ]
        
        # Second search for additional splits that aren't adjacent
        additional_result = [
            {
                'entity': {
                    'metadata': {'split_num': 1},
                    'text': 'This is the first split.'
                }
            },
            {
                'entity': {
                    'metadata': {'split_num': 10},
                    'text': 'This is the tenth split.'
                }
            }
        ]
        
        # Configure milvus_client_mock to return different values on consecutive calls
        self.milvus_client_mock.search.side_effect = [[adjacent_result], [additional_result]]
        
        # Execute
        result = self.merge_splits(
            self.milvus_client_mock,
            self.text_embedding_mock,
            self.code_embedding_mock,
            fetched_doc,
            'test_collection',
            'link_key',
            'link1',
            code=False,
            merge_limit=7
        )
        
        # Assert
        expected_text = 'This is the first split.\n\n...truncated...\n\nThis is the fourth split.\nThis is the fifth split.\nThis is the sixth split.\n\n...truncated...\n\nThis is the tenth split.'
        self.assertEqual(result['entity']['text'], expected_text)
        self.assertEqual(self.milvus_client_mock.search.call_count, 2)
    
    def test_no_duplicate_vectors(self):
        """Test that no duplicate vectors are included in the result"""
        # Setup
        fetched_doc = {
            'entity': {
                'metadata': {'split_num': 2},
                'text': 'This is the second split.'
            }
        }
        
        # First search for adjacent splits where one split appears twice
        adjacent_result = [
            {
                'entity': {
                    'metadata': {'split_num': 1},
                    'text': 'This is the first split.'
                }
            },
            {
                'entity': {
                    'metadata': {'split_num': 3},
                    'text': 'This is the third split.'
                }
            }
        ]

        # Second search for additional splits that aren't adjacent
        additional_result = [
            {
                'entity': {
                    'metadata': {'split_num': 1},
                    'text': 'This is the first split.'
                }
            }
        ]

        # Configure milvus_client_mock to return different values on consecutive calls
        self.milvus_client_mock.search.side_effect = [[adjacent_result], [additional_result]]
        
        # Execute
        result = self.merge_splits(
            self.milvus_client_mock,
            self.text_embedding_mock,
            self.code_embedding_mock,
            fetched_doc,
            'test_collection',
            'link_key',
            'link1',
            code=False,
            merge_limit=4
        )
        
        # Assert - should only include one version of split 1
        expected_text = 'This is the first split.\nThis is the second split.\nThis is the third split.'
        self.assertEqual(result['entity']['text'], expected_text)
        self.assertEqual(self.milvus_client_mock.search.call_count, 2)

    def test_unlimited_merge(self):
        """Test when merge_limit is None (should get all splits)"""
        # Setup
        fetched_doc = {
            'entity': {
                'metadata': {'split_num': 2},
                'text': 'This is the second split.'
            }
        }

        result = [
            {
                'entity': {
                    'metadata': {'split_num': 1},
                    'text': 'This is the first split.'
                }
            },
            {
                'entity': {
                    'metadata': {'split_num': 3},
                    'text': 'This is the third split.'
                }
            },
                        {
                'entity': {
                    'metadata': {'split_num': 2},  # This is the original fetched doc
                    'text': 'This is the second split.'
                }
            },
            {
                'entity': {
                    'metadata': {'split_num': 4},
                    'text': 'This is the fourth split.'
                }
            },
            {
                'entity': {
                    'metadata': {'split_num': 5},
                    'text': 'This is the fifth split.'
                }
            },
            {
                'entity': {
                    'metadata': {'split_num': 6},
                    'text': 'This is the sixth split.'
                }
            }
        ]
        
        self.milvus_client_mock.search.return_value = [result] # A single list, because a single search is done when merge_limit is None
        
        # Execute
        result = self.merge_splits(
            self.milvus_client_mock,
            self.text_embedding_mock,
            self.code_embedding_mock,
            fetched_doc,
            'test_collection',
            'link_key',
            'link1',
            code=False,
            merge_limit=None
        )
        
        # Assert - should include all splits with truncation between non-adjacent
        expected_text = 'This is the first split.\nThis is the second split.\nThis is the third split.\nThis is the fourth split.\nThis is the fifth split.\nThis is the sixth split.'
        self.assertEqual(result['entity']['text'], expected_text)
        self.assertEqual(self.milvus_client_mock.search.call_count, 1)

    def test_excel_single_sheet_continuous(self):
        """Test merging Excel document with a single sheet and continuous splits"""
        # Setup
        fetched_doc = {
            'entity': {
                'metadata': {'type': 'EXCEL', 'split_num': 1},
                'text': '''## References
| Last Update Date | Data Source Type | Data Source Title | Referenced Count |
| --- | --- | --- | --- |
| 2025-04-09 08:41 | Codebase | ARCHITECTURE.md | 59 |
| 2025-04-09 08:41 | Codebase | views.py | 4 |'''
            }
        }
        
        # Mock the search for adjacent splits
        adjacent_result = [{
            'entity': {
                'metadata': {'type': 'EXCEL', 'split_num': 2},
                'text': '''## References
| Last Update Date | Data Source Type | Data Source Title | Referenced Count |
| 2025-04-09 08:41 | Codebase | utils.py | 3 |
| 2025-04-09 08:41 | Codebase | README.md | 2 |'''
            }
        }]
        self.milvus_client_mock.search.return_value = [adjacent_result]
        
        # Execute
        result = self.merge_splits(
            self.milvus_client_mock,
            self.text_embedding_mock,
            self.code_embedding_mock,
            fetched_doc,
            'test_collection',
            'link_key',
            'link1',
            code=False,
            merge_limit=4
        )
        
        # Assert
        expected_text = '''## References
| Last Update Date | Data Source Type | Data Source Title | Referenced Count |
| --- | --- | --- | --- |
| 2025-04-09 08:41 | Codebase | ARCHITECTURE.md | 59 |
| 2025-04-09 08:41 | Codebase | views.py | 4 |
| 2025-04-09 08:41 | Codebase | utils.py | 3 |
| 2025-04-09 08:41 | Codebase | README.md | 2 |'''
        self.assertEqual(result['entity']['text'], expected_text)

    def test_excel_multiple_sheets_continuous(self):
        """Test merging Excel document with multiple sheets and continuous splits"""
        # Setup
        fetched_doc = {
            'entity': {
                'metadata': {'type': 'EXCEL', 'split_num': 1},
                'text': '''## References
| Last Update Date | Data Source Type | Data Source Title | Referenced Count |
| --- | --- | --- | --- |
| 2025-04-09 08:41 | Codebase | ARCHITECTURE.md | 59 |'''
            }
        }
        
        # Mock the search for adjacent splits
        adjacent_result = [
            {
                'entity': {
                    'metadata': {'type': 'EXCEL', 'split_num': 2},
                    'text': '''## References
| Last Update Date | Data Source Type | Data Source Title | Referenced Count |
| 2025-04-09 08:41 | Codebase | views.py | 4 |'''
                }
            },
            {
                'entity': {
                    'metadata': {'type': 'EXCEL', 'split_num': 3},
                    'text': '''## Questions
| Datetime | Source | Question | Trust Score | Follow-up |
| --- | --- | --- | --- | --- |
| 2025-04-06 08:31 | Widget | how does gurubase work? | 0.90 | False |'''
                }
            }
        ]
        self.milvus_client_mock.search.return_value = [adjacent_result]
        
        # Execute
        result = self.merge_splits(
            self.milvus_client_mock,
            self.text_embedding_mock,
            self.code_embedding_mock,
            fetched_doc,
            'test_collection',
            'link_key',
            'link1',
            code=False,
            merge_limit=4
        )
        
        # Assert
        expected_text = '''## References
| Last Update Date | Data Source Type | Data Source Title | Referenced Count |
| --- | --- | --- | --- |
| 2025-04-09 08:41 | Codebase | ARCHITECTURE.md | 59 |
| 2025-04-09 08:41 | Codebase | views.py | 4 |

## Questions
| Datetime | Source | Question | Trust Score | Follow-up |
| --- | --- | --- | --- | --- |
| 2025-04-06 08:31 | Widget | how does gurubase work? | 0.90 | False |'''
        self.assertEqual(result['entity']['text'], expected_text)

    def test_excel_multiple_sheets_with_gaps(self):
        """Test merging Excel document with multiple sheets and non-adjacent splits"""
        # Setup
        fetched_doc = {
            'entity': {
                'metadata': {'type': 'EXCEL', 'split_num': 1},
                'text': '''## References
| Last Update Date | Data Source Type | Data Source Title | Referenced Count |
| --- | --- | --- | --- |
| 2025-04-09 08:41 | Codebase | ARCHITECTURE.md | 59 |'''
            }
        }
        
        # Mock the search for adjacent splits
        adjacent_result = [
            {
                'entity': {
                    'metadata': {'type': 'EXCEL', 'split_num': 3},
                    'text': '''## References
| Last Update Date | Data Source Type | Data Source Title | Referenced Count |
| 2025-04-09 08:41 | Codebase | views.py | 4 |'''
                }
            },
            {
                'entity': {
                    'metadata': {'type': 'EXCEL', 'split_num': 4},
                    'text': '''## Questions
| Datetime | Source | Question | Trust Score | Follow-up |
| --- | --- | --- | --- | --- |
| 2025-04-06 08:31 | Widget | how does gurubase work? | 0.90 | False |'''
                }
            }
        ]
        self.milvus_client_mock.search.return_value = [adjacent_result]
        
        # Execute
        result = self.merge_splits(
            self.milvus_client_mock,
            self.text_embedding_mock,
            self.code_embedding_mock,
            fetched_doc,
            'test_collection',
            'link_key',
            'link1',
            code=False,
            merge_limit=4
        )
        
        # Assert
        expected_text = '''## References
| Last Update Date | Data Source Type | Data Source Title | Referenced Count |
| --- | --- | --- | --- |
| 2025-04-09 08:41 | Codebase | ARCHITECTURE.md | 59 |

...truncated...

| 2025-04-09 08:41 | Codebase | views.py | 4 |

## Questions
| Datetime | Source | Question | Trust Score | Follow-up |
| --- | --- | --- | --- | --- |
| 2025-04-06 08:31 | Widget | how does gurubase work? | 0.90 | False |'''
        self.assertEqual(result['entity']['text'], expected_text)

    def test_excel_multiple_sheets_with_gaps_and_new_sheet(self):
        """Test merging Excel document with multiple sheets, gaps, and new sheet in the middle"""
        # Setup
        fetched_doc = {
            'entity': {
                'metadata': {'type': 'EXCEL', 'split_num': 1},
                'text': '''## References
| Last Update Date | Data Source Type | Data Source Title | Referenced Count |
| --- | --- | --- | --- |
| 2025-04-09 08:41 | Codebase | ARCHITECTURE.md | 59 |'''
            }
        }
        
        # Mock the search for adjacent splits
        adjacent_result = [
            {
                'entity': {
                    'metadata': {'type': 'EXCEL', 'split_num': 3},
                    'text': '''## References
| Last Update Date | Data Source Type | Data Source Title | Referenced Count |
| 2025-04-09 08:41 | Codebase | views.py | 4 |'''
                }
            },
            {
                'entity': {
                    'metadata': {'type': 'EXCEL', 'split_num': 4},
                    'text': '''## Unable to Answer
| Datetime | Source | Question |
| --- | --- | --- |
| 2025-04-09 07:08 | Github | in more detail |'''
                }
            },
            {
                'entity': {
                    'metadata': {'type': 'EXCEL', 'split_num': 5},
                    'text': '''## Questions
| Datetime | Source | Question | Trust Score | Follow-up |
| --- | --- | --- | --- | --- |
| 2025-04-06 08:31 | Widget | how does gurubase work? | 0.90 | False |'''
                }
            }
        ]
        self.milvus_client_mock.search.return_value = [adjacent_result]
        
        # Execute
        result = self.merge_splits(
            self.milvus_client_mock,
            self.text_embedding_mock,
            self.code_embedding_mock,
            fetched_doc,
            'test_collection',
            'link_key',
            'link1',
            code=False,
            merge_limit=4
        )
        
        # Assert
        expected_text = '''## References
| Last Update Date | Data Source Type | Data Source Title | Referenced Count |
| --- | --- | --- | --- |
| 2025-04-09 08:41 | Codebase | ARCHITECTURE.md | 59 |

...truncated...

| 2025-04-09 08:41 | Codebase | views.py | 4 |

## Unable to Answer
| Datetime | Source | Question |
| --- | --- | --- |
| 2025-04-09 07:08 | Github | in more detail |

## Questions
| Datetime | Source | Question | Trust Score | Follow-up |
| --- | --- | --- | --- | --- |
| 2025-04-06 08:31 | Widget | how does gurubase work? | 0.90 | False |'''
        self.assertEqual(result['entity']['text'], expected_text)

if __name__ == '__main__':
    unittest.main()