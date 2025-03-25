import logging
from django.conf import settings
from pymilvus import DataType, MilvusClient
import traceback
logger = logging.getLogger(__name__)

client = MilvusClient(
    uri = f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}"
)

def drop_collection(collection_name):
    try:
        client.drop_collection(collection_name)
    except Exception as e:
        logger.error(f'Exception while dropping collection {collection_name}: {traceback.format_exc()}')

    logger.info(f'Dropped collection {collection_name}')

def create_similarity_collection(collection_name):
    # 1. Create schema
    schema = MilvusClient.create_schema(
        enable_dynamic_field=False,
    )

    # 2. Add fields to schema
    schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name='on_sitemap', datatype=DataType.BOOL)
    schema.add_field(field_name="description_vector", datatype=DataType.FLOAT_VECTOR, dim=1024)
    schema.add_field(field_name="title_vector", datatype=DataType.FLOAT_VECTOR, dim=1024)
    schema.add_field(field_name="content_vector", datatype=DataType.FLOAT_VECTOR, dim=1024)
    schema.add_field(field_name="title", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(field_name="slug", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(field_name="guru_type", datatype=DataType.VARCHAR, max_length=65535)

    logger.info(f'Created schema for collection {collection_name}')

    # 3. Prepare index parameters
    index_params = client.prepare_index_params()

    # 4. Add indexes
    index_params.add_index(
        field_name="id",
        index_type="STL_SORT"
    )

    index_params.add_index(
        field_name="description_vector", 
        index_type="AUTOINDEX",
        metric_type="L2",
    )

    index_params.add_index(
        field_name="title_vector", 
        index_type="AUTOINDEX",
        metric_type="L2",
    )

    index_params.add_index(
        field_name="content_vector", 
        index_type="AUTOINDEX",
        metric_type="L2",
    )

    index_params.add_index(
        field_name="guru_type", 
        index_type="AUTOINDEX",
        metric_type="L2",
    )

    logger.info(f'Added indexes to collection {collection_name}')

    # 3. Create a collection
    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params
    )

    logger.info(f'Created collection {collection_name}')


def create_context_collection(collection_name, dimension):
    # 1. Create schema
    schema = MilvusClient.create_schema(
        auto_id=True,
        enable_dynamic_field=False,
    )

    # 2. Add fields to schema
    schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=dimension)
    schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(field_name='metadata', datatype=DataType.JSON)

    print(f'Created schema for collection {collection_name}')

    # 3. Prepare index parameters
    index_params = client.prepare_index_params()

    # 4. Add indexes
    index_params.add_index(
        field_name="id",
        index_type="STL_SORT"
    )

    index_params.add_index(
        field_name="vector", 
        index_type="AUTOINDEX",
        metric_type="COSINE",
    )

    print(f'Added indexes to collection {collection_name}')

    # 3. Create a collection
    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params
    )

    print(f'Created collection {collection_name}')

def create_code_context_collection(collection_name, dimension):
    if client.has_collection(collection_name):
        return
    # 1. Create schema
    schema = MilvusClient.create_schema(
        auto_id=True,
        enable_dynamic_field=False,
    )

    # 2. Add fields to schema
    schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=dimension)
    schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(field_name='metadata', datatype=DataType.JSON)
    schema.add_field(field_name='guru_slug', datatype=DataType.VARCHAR, max_length=65535)

    print(f'Created schema for collection {collection_name}')

    # 3. Prepare index parameters
    index_params = client.prepare_index_params()

    # 4. Add indexes
    index_params.add_index(
        field_name="id",
        index_type="STL_SORT"
    )

    index_params.add_index(
        field_name="vector", 
        index_type="AUTOINDEX",
        metric_type="COSINE",
    )

    index_params.add_index(
        field_name="guru_slug", 
        index_type="AUTOINDEX",
        metric_type="L2",
    )

    print(f'Added indexes to collection {collection_name}')

    # 3. Create a collection
    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params
    )

    print(f'Created collection {collection_name}')


def collection_exists(collection_name):
    return client.has_collection(collection_name=collection_name)

    
def insert_vectors(collection_name, docs, code=False, dimension=None):
    assert dimension is not None, "Milvus insert_vectors: Dimension must be provided"

    if not client.has_collection(collection_name):
        if code:
            create_code_context_collection(collection_name, dimension)
        else:
            create_context_collection(collection_name, dimension)

    try:
        result = client.insert(
            collection_name=collection_name,
            data=docs,
        )
    except Exception as e:
        logger.error(f'Exception while inserting vectors into collection {collection_name}: {traceback.format_exc()}')
        raise e

    ids = result['ids']

    # logger.info(f'Upserted {len(docs)} vectors into collection {collection_name}')

    return ids


def delete_vectors(collection_name, ids):
    if not client.has_collection(collection_name):
        return

    try:
        client.delete(
            collection_name=collection_name,
            ids=ids
        )
    except Exception as e:
        logger.error(f'Exception while deleting vectors from collection {collection_name}: {traceback.format_exc()}')

    # logger.info(f'Deleted {len(ids)} vectors from collection {collection_name}')


def delete_vectors_by_filter(collection_name, filter):
    if not client.has_collection(collection_name):
        return

    try:
        response = client.delete(
            collection_name=collection_name,
            filter=filter
        )
    except Exception as e:
        logger.error(f'Exception while deleting vectors from collection {collection_name}: {traceback.format_exc()}')

    # logger.info(f'Deleted {response["delete_count"]} vectors from collection {collection_name}')


def search_for_closest(collection_name, vector, guru_type, sitemap_constraint, top_k=1, column='title'):
    if column not in ['title', 'description', 'content']:
        raise ValueError(f'Invalid column: {column}')

    
    try:
        anns_field = f'{column}_vector'
        if sitemap_constraint:
            filter = f'on_sitemap == True and guru_type == "{guru_type}"'
        else:
            filter = f'guru_type == "{guru_type}"'

        results = client.search(
            collection_name=collection_name,
            data=[vector],
            anns_field=anns_field,
            top_k=top_k + 1, # +1 to exclude the query vector itself
            output_fields=['title', 'slug'],
            filter=filter
        )
    except Exception as e:
        logger.error(f'Exception while searching for closest vectors in collection {collection_name}: {traceback.format_exc()}')
        return []

    # order by distance
    results = sorted(results[0], key=lambda x: x['distance'])

    return results


def delete_non_positive_scores(collection_name):
    filter = f'metadata["score"] <= 0'
    try:
        client.delete(
            collection_name=collection_name,
            filter=filter
        )
    except Exception as e:
        logger.error(f'Exception while deleting vectors from collection {collection_name}: {traceback.format_exc()}')

    logger.info(f'Deleted non-positive score vectors from collection {collection_name}')


def rename_collection(old_collection_name, new_collection_name):
    try:
        client.rename_collection(old_collection_name, new_collection_name)
    except Exception as e:
        logger.error(f'Exception while renaming collection {old_collection_name} to {new_collection_name}: {traceback.format_exc()}')

    logger.info(f'Renamed collection {old_collection_name} to {new_collection_name}')

        
def upsert_vectors(collection_name, docs):
    if not client.has_collection(collection_name):
        create_context_collection(collection_name)

    try:
        result = client.upsert(
            collection_name=collection_name,
            data=docs,
        )
    except Exception as e:
        logger.error(f'Exception while upserting vectors into collection {collection_name}: {traceback.format_exc()}')

    # logger.info(f'Upserted {len(docs)} vectors into collection {collection_name}')

    return result

    
def fetch_vectors(collection_name, filter, output_fields=None):
    if not client.has_collection(collection_name):
        return []

    try:
        results = client.query(
            collection_name=collection_name,
            filter=filter,
            output_fields=output_fields
        )
    except Exception as e:
        logger.error(f'Exception while fetching vectors from collection {collection_name}: {traceback.format_exc()}')
        return []

    return results
