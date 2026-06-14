from django.conf import settings
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
)


VECTOR_SIZE = 3072


def get_qdrant_client():
    if not settings.QDRANT_URL:
        raise ValueError("QDRANT_URL is missing in .env")

    if not settings.QDRANT_API_KEY:
        raise ValueError("QDRANT_API_KEY is missing in .env")

    return QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
        timeout=60,
    )


def ensure_collection():
    client = get_qdrant_client()
    collection_name = settings.QDRANT_COLLECTION_NAME

    collections = client.get_collections().collections
    collection_names = [collection.name for collection in collections]

    if collection_name not in collection_names:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )

    ensure_payload_indexes(client, collection_name)


def ensure_payload_indexes(client, collection_name):
    """
    Required because Qdrant Cloud may require indexes
    for filtered payload fields like owner_id/material_id.
    """

    index_fields = {
        "owner_id": PayloadSchemaType.INTEGER,
        "material_id": PayloadSchemaType.INTEGER,
        "chunk_id": PayloadSchemaType.INTEGER,
    }

    for field_name, schema_type in index_fields.items():
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=schema_type,
            )
        except Exception:
            # Ignore if index already exists
            pass


def upsert_chunk_embedding(point_id, vector, payload):
    ensure_collection()

    client = get_qdrant_client()

    client.upsert(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        ],
    )


def search_similar_chunks(query_vector, owner_id, material_id=None, limit=5):
    ensure_collection()

    client = get_qdrant_client()

    conditions = [
        FieldCondition(
            key="owner_id",
            match=MatchValue(value=int(owner_id)),
        )
    ]

    if material_id:
        conditions.append(
            FieldCondition(
                key="material_id",
                match=MatchValue(value=int(material_id)),
            )
        )

    result = client.query_points(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        query=query_vector,
        query_filter=Filter(must=conditions),
        limit=limit,
        with_payload=True,
    )

    return result