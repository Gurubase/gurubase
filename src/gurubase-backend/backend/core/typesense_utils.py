from django.conf import settings
import typesense
import logging
from core.guru_types import get_guru_type_object

logger = logging.getLogger(__name__)


class TypeSenseClient():
    
    def __init__(self, guru_type):
        self.client = typesense.Client({
            'api_key': settings.TYPESENSE_API_KEY,
            'nodes': [{
                'host': settings.TYPESENSE_HOST,
                'port': settings.TYPESENSE_PORT,
                'protocol': settings.TYPESENSE_PROTOCOL
            }],
            'connection_timeout_seconds': 20
        })

        guru_type_obj = get_guru_type_object(guru_type, only_active=False)
        self.collection_name = guru_type_obj.typesense_collection_name

        self.guru_type = guru_type

        try:
            self.client.collections[self.collection_name].retrieve()
        except Exception as e:
            self.create_collection()

    def create_collection(self):
        schema = {
            'name': self.collection_name,
            'fields': [
                # No facets as we don't have any way to group questions
                # From the docs (https://typesense.org/docs/guide/building-a-search-application.html#creating-a-books-collection)
                # "A facet field allows us to cluster the search results into categories and lets us drill into each of those categories."
                {'name': 'id', 'type': 'string'},
                {'name': 'slug', 'type': 'string'},
                {'name': 'question', 'type': 'string'},
                # {'name': 'content', 'type': 'string'},
                # {'name': 'description', 'type': 'string'},
                # {'name': 'change_count', 'type': 'int32'},
            ],
        }
        
        try:
            self.client.collections.create(schema)
        except Exception as e:
            logger.error(f"Error creating collection for {self.guru_type}: {e}", exc_info=True)
        
    def get_collection(self):
        return self.client.collections[self.collection_name]
    
    def get_document(self, document_id):
        return self.get_collection().documents[document_id]
    
    def create_document(self, document):
        return self.get_collection().documents.create(document)
    
    def update_document(self, document_id, document):
        return self.get_document(document_id).update(document)
    
    def delete_document(self, document_id):
        return self.get_document(document_id).delete()
    
    def delete_documents(self):
        result = self.get_collection().documents.delete({'filter_by': 'slug:!=""'})
        logger.info(f"Deleted {result['num_deleted']} documents from {self.collection_name}")
    
    def delete_collection(self):
        return self.client.collections[self.collection_name].delete()
    
    def search(self, question):
        search_params = {
            'q': question,
            'query_by': 'question',
            'max_hits': 10,
            'num_typos': 0,
            'include_fields': 'question, description, slug',
        }
        return self.get_collection().documents.search(search_params)
    
    def import_documents(self, documents):
        return self.get_collection().documents.import_(documents, {'action': 'upsert'})
    
    
def parse_typesense_result(result):
    parsed = []
    hits = result['hits']
    for hit in hits:
        obj = {
            'document': hit['document'],
            'highlights': hit['highlights'],
        }
        parsed.append(obj)
    
    return parsed