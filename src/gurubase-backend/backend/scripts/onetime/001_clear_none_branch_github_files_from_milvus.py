import os
import sys
import random

import django
sys.path.append('/workspaces/gurubase/src/gurubase-backend/backend')
sys.path.append('/workspaces/gurubase-backend/backend')
sys.path.append('/workspace/backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from core.milvus_utils import client, fetch_vectors, delete_vectors_by_filter, insert_vectors

COLLECTIONS = {
    "IN_HOUSE": {
        "dimension": 1024,
        "collection_name": "github_repo_code"
    },
    "GEMINI_EMBEDDING_001": {
        "dimension": 768,
        "collection_name": "github_repo_code_gemini_embedding_001"
    },
    "GEMINI_TEXT_EMBEDDING_004": {
        "dimension": 768,
        "collection_name": "github_repo_code_gemini_text_embedding_004"
    },
    "OPENAI_TEXT_EMBEDDING_3_LARGE": {
        "dimension": 3072,
        "collection_name": "github_repo_code_openai_text_embedding_3_large"
    },
    "OPENAI_TEXT_EMBEDDING_3_SMALL": {
        "dimension": 1536,
        "collection_name": "github_repo_code_openai_text_embedding_3_small"
    },
    "OPENAI_TEXT_EMBEDDING_ADA_002": {
        "dimension": 1536,
        "collection_name": "github_repo_code_openai_ada_002"
    }
}

def insert_test_vector():
    # Choose a random collection for testing
    model_name = random.choice(list(COLLECTIONS.keys()))
    config = COLLECTIONS[model_name]
    collection_name = config["collection_name"]
    dimension = config["dimension"]
    
    print(f"\nInserting test vector into collection: {collection_name}")
    
    # Create a random vector of the correct dimension
    test_vector = [random.random() for _ in range(dimension)]
    
    # Create test data with None branch
    test_data = {
        "vector": test_vector,
        "text": "Test content with None branch",
        "metadata": {"type":"GITHUB_REPO","repo_link":"https://github.com/Gurubase/gurubase-widget","link":"https://github.com/Gurubase/gurubase-widget/tree/None/build.js","repo_title":"Gurubase/gurubase-widget","title":"build.js","file_path":"build.js","split_num":1},
        "guru_slug": "test"
    }
    
    # Insert the test vector
    insert_vectors(collection_name, [test_data], code=True, dimension=dimension)
    print(f"Inserted test vector into {collection_name}")

def check_and_delete_none_branch():
    total_count = 0
    
    for model_name, config in COLLECTIONS.items():
        collection_name = config["collection_name"]
        print(f"\nChecking collection: {collection_name}")

        if not client.has_collection(collection_name):
            print(f"Collection {collection_name} does not exist. Skipping...")
            continue
        
        # Query for elements with None branch
        filter = 'metadata["link"] like "%None%"'
        results = fetch_vectors(collection_name, filter)
        
        count = len(results)
        total_count += count
        print(f"Found {count} elements with None branch")
        
        if count > 0:
            print("Sample metadata:")
            for i, result in enumerate(results[:3]):  # Show first 3 samples
                print(f"Sample {i+1}: {result.get('metadata', {})}")
    
    print(f"\nTotal elements found across all collections: {total_count}")
    
    if total_count > 0:
        response = input("\nDo you want to delete these elements? (yes/no): ")
        if response.lower() == 'yes':
            for model_name, config in COLLECTIONS.items():
                collection_name = config["collection_name"]
                print(f"\nDeleting from collection: {collection_name}")
                filter = 'metadata["link"] like "%None%"'
                delete_vectors_by_filter(collection_name, filter)
            print("\nDeletion completed!")
        else:
            print("\nOperation cancelled.")
    else:
        print("\nNo elements to delete.")

if __name__ == "__main__":
    # First insert a test vector
    # insert_test_vector()
    
    # Then check and delete
    check_and_delete_none_branch()


