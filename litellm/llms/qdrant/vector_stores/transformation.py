from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

import httpx

import litellm
from litellm.llms.base_llm.vector_store.transformation import BaseVectorStoreConfig
from litellm.secret_managers.main import get_secret_str
from litellm.types.router import GenericLiteLLMParams
from litellm.types.vector_stores import (
    BaseVectorStoreAuthCredentials,
    VectorStoreCreateOptionalRequestParams,
    VectorStoreCreateResponse,
    VectorStoreIndexEndpoints,
    VectorStoreResultContent,
    VectorStoreSearchOptionalRequestParams,
    VectorStoreSearchResponse,
    VectorStoreSearchResult,
)

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj
    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any

QDRANT_OPTIONAL_PARAMS = {
    "limit",
    "offset",
    "filter",
    "search_params",
    "with_payload",
    "with_vectors",
    "score_threshold",
}


class QdrantVectorStoreConfig(BaseVectorStoreConfig):
    """
    Configuration for Qdrant Vector Store
    
    This implementation uses the Qdrant REST API for vector store operations.
    Supports vector search with embeddings generated via litellm.embeddings.
    """

    def __init__(self):
        super().__init__()

    def validate_environment(
        self, headers: dict, litellm_params: Optional[GenericLiteLLMParams]
    ) -> dict:
        api_key: Optional[str] = None
        if litellm_params is not None:
            api_key = litellm_params.api_key or get_secret_str("QDRANT_API_KEY")

        if api_key:
            headers.update({"api-key": api_key})

        return headers

    def get_auth_credentials(
        self, litellm_params: dict
    ) -> BaseVectorStoreAuthCredentials:
        api_key = litellm_params.get("api_key")
        if not api_key:
            api_key = get_secret_str("QDRANT_API_KEY")
            
        credentials = {}
        if api_key:
            credentials["headers"] = {"api-key": api_key}
        return credentials

    def get_vector_store_endpoints_by_type(self) -> VectorStoreIndexEndpoints:
        return {
            "read": [
                ("POST", "/collections/{collection_name}/points/search"),
                ("GET", "/collections/{collection_name}/points/{point_id}"),
                ("POST", "/collections/{collection_name}/points"),
            ],
            "write": [
                ("PUT", "/collections/{collection_name}/points"),
                ("POST", "/collections/{collection_name}/points/delete"),
                ("PUT", "/collections/{collection_name}"),
            ],
        }

    def map_openai_params(
        self, non_default_params: dict, optional_params: dict, drop_params: bool
    ) -> dict:
        for param, value in non_default_params.items():
            if param in QDRANT_OPTIONAL_PARAMS:
                optional_params[param] = value
        return optional_params

    def get_complete_url(
        self,
        api_base: Optional[str],
        litellm_params: dict,
    ) -> str:
        """
        Get the base endpoint for Qdrant API
        
        Expected format: https://{qdrant_api_base}:6333 or https://cloud.qdrant.io
        """
        api_base = api_base or get_secret_str("QDRANT_API_BASE")

        if not api_base:
            raise ValueError(
                "Qdrant API base URL is required. Set QDRANT_API_BASE environment variable or pass api_base in litellm_params."
            )

        if api_base:
            return api_base.rstrip("/")

        return api_base

    def transform_search_vector_store_request(
        self,
        vector_store_id: str,
        query: Union[str, List[str]],
        vector_store_search_optional_params: VectorStoreSearchOptionalRequestParams,
        api_base: str,
        litellm_logging_obj: LiteLLMLoggingObj,
        litellm_params: dict,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Transform search request for Qdrant API
        
        Generates embeddings using litellm.embeddings and constructs Qdrant search request
        """
        # Convert query to string if it's a list
        if isinstance(query, list):
            query = " ".join(query)

        # Get embedding model from litellm_params (required)
        embedding_model = litellm_params.get("litellm_embedding_model")
        if not embedding_model:
            raise ValueError(
                "embedding_model is required in litellm_params for Qdrant. You can call any litellm embedding model."
                "Example: litellm_params['embedding_model'] = 'azure/text-embedding-3-large'"
            )

        embedding_config = litellm_params.get("litellm_embedding_config", {})
        
        # Get limit (number of results to return)
        limit = vector_store_search_optional_params.get("limit", 10)
        
        # Generate embedding for the query using litellm.embeddings
        try:
            embedding_response = litellm.embedding(
                model=embedding_model,
                input=[query],
                **embedding_config,
            )
            query_vector = embedding_response.data[0]["embedding"]
        except Exception as e:
            raise Exception(f"Failed to generate embedding for query: {str(e)}")

        # Qdrant search endpoint
        collection_name = vector_store_id  # vector_store_id is the collection name
        url = f"{api_base}/collections/{collection_name}/points/search"

        # Build the request body for Qdrant search
        request_body = {
            "vector": query_vector,
            "limit": limit,
            **vector_store_search_optional_params,
        }

        #########################################################
        # Update logging object with details of the request
        #########################################################
        litellm_logging_obj.model_call_details["input"] = query
        litellm_logging_obj.model_call_details["embedding_model"] = embedding_model

        return url, request_body

    def transform_search_vector_store_response(
        self, response: httpx.Response, litellm_logging_obj: LiteLLMLoggingObj
    ) -> VectorStoreSearchResponse:
        """
        Transform Qdrant API response to standard vector store search response
        
        Handles the format from Qdrant which returns:
        {
            "result": {
                "points": [
                    {
                        "id": "...",
                        "payload": {...},
                        "vector": [...],
                        "score": 0.95
                    }
                ]
            }
        }
        """
        try:
            response_json = response.json()

            # Extract results from Qdrant API response
            points = response_json.get("result", {}).get("points", [])

            # Transform results to standard format
            search_results: List[VectorStoreSearchResult] = []
            for point in points:
                # Extract payload content
                payload = point.get("payload", {})
                
                # Try to get text content from common payload fields
                text_content = ""
                for field in ["text", "content", "document"]:
                    if field in payload:
                        text_content = str(payload[field])
                        break
                
                content = [
                    VectorStoreResultContent(
                        text=text_content,
                        type="text",
                    )
                ]

                # Get the search score
                score = point.get("score", 0.0)

                # Build attributes with all available metadata
                attributes = {}
                for key, value in payload.items():
                    if key not in ["text", "content", "document"]:
                        attributes[key] = value

                result_obj = VectorStoreSearchResult(
                    score=score,
                    content=content,
                    file_id=str(point.get("id")),
                    filename=None,
                    attributes=attributes,
                )
                search_results.append(result_obj)

            return VectorStoreSearchResponse(
                object="vector_store.search_results.page",
                search_query=litellm_logging_obj.model_call_details.get("input", ""),
                data=search_results,
            )

        except Exception as e:
            raise self.get_error_class(
                error_message=str(e),
                status_code=response.status_code,
                headers=response.headers,
            )

    def transform_create_vector_store_request(
        self,
        vector_store_create_optional_params: VectorStoreCreateOptionalRequestParams,
        api_base: str,
    ) -> Tuple[str, Dict]:
        """
        Transform create vector store request for Qdrant API
        
        Creates a new collection in Qdrant
        """
        collection_name = vector_store_create_optional_params.get("name")
        if not collection_name:
            raise ValueError("Collection name is required for Qdrant vector store creation")

        # Qdrant create collection endpoint
        url = f"{api_base}/collections/{collection_name}"

        # Default vector parameters
        vector_params = {
            "size": 1536,  # Default size for text-embedding-ada-002
            "distance": "Cosine"
        }

        # Check if vector configuration is provided in metadata
        metadata = vector_store_create_optional_params.get("metadata", {})
        if metadata and "vector_size" in metadata:
            vector_params["size"] = metadata["vector_size"]
        if metadata and "distance" in metadata:
            vector_params["distance"] = metadata["distance"]

        # Build the request body for Qdrant collection creation
        request_body = {
            "vectors": vector_params
        }

        # Add any additional parameters from metadata
        if metadata:
            for key, value in metadata.items():
                if key not in ["vector_size", "distance"]:
                    request_body[key] = value

        return url, request_body

    def transform_create_vector_store_response(
        self, response: httpx.Response
    ) -> VectorStoreCreateResponse:
        """
        Transform Qdrant API response to standard vector store create response
        """
        try:
            response_json = response.json()
            
            # For Qdrant, a successful creation returns a simple acknowledgment
            # We'll create a standard response based on the request
            result = VectorStoreCreateResponse(
                id="",  # Will be set by the caller
                object="vector_store",
                created_at=int(litellm.utils.get_utc_timestamp()),
                name="",  # Will be set by the caller
                bytes=0,
                file_counts={
                    "in_progress": 0,
                    "completed": 0,
                    "failed": 0,
                    "cancelled": 0,
                    "total": 0
                },
                status="completed",
                expires_after=None,
                expires_at=None,
                last_active_at=None,
                metadata={}
            )
            
            return result

        except Exception as e:
            raise self.get_error_class(
                error_message=str(e),
                status_code=response.status_code,
                headers=response.headers,
            )