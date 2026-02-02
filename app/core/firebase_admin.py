"""
Firebase Admin SDK initialization and utilities
"""
import firebase_admin
from firebase_admin import credentials, firestore, storage as fb_storage, auth
from app.config import settings
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Global Firebase instances
db = None
storage = None


def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    global db, storage

    try:
        # Check if already initialized
        firebase_admin.get_app()
        logger.info("Firebase already initialized")
    except ValueError:
        # Initialize Firebase Admin
        cred_path = settings.firebase_service_account_path
        logger.info(f"Firebase service account path: {cred_path}")
        logger.info(f"Firebase project ID: {settings.firebase_project_id}")
        logger.info(f"Firebase storage bucket: {settings.firebase_storage_bucket}")

        try:
            if os.path.exists(cred_path):
                logger.info("Using service account file for credentials")
                cred = credentials.Certificate(cred_path)
            else:
                logger.info("Using Application Default Credentials (Cloud Run)")
                cred = credentials.ApplicationDefault()

            firebase_admin.initialize_app(cred, {
                'storageBucket': settings.firebase_storage_bucket,
                'projectId': settings.firebase_project_id
            })
            logger.info("Firebase Admin SDK initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise

    # Initialize Firestore
    try:
        db = firestore.client()
        logger.info("Firestore client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Firestore: {e}")
        raise

    # Initialize Storage
    try:
        storage = fb_storage.bucket()
        logger.info("Firebase Storage initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Storage: {e}")
        # Storage is optional, don't raise

    return db, storage


def get_firestore():
    """Get Firestore client"""
    global db
    if db is None:
        initialize_firebase()
    return db


def get_storage():
    """Get Firebase Storage bucket"""
    global storage
    if storage is None:
        initialize_firebase()
    return storage


def get_auth():
    """Get Firebase Auth instance"""
    return auth


# Helper functions for Firestore operations
async def get_document(collection: str, doc_id: str) -> dict | None:
    """Get a single document from Firestore"""
    db = get_firestore()
    doc = db.collection(collection).document(doc_id).get()
    if doc.exists:
        data = doc.to_dict()
        data['id'] = doc.id
        return data
    return None


async def get_collection(
    collection: str,
    limit: int = 100,
    order_by: str = None,
    order_direction: str = 'DESCENDING',
    filters: list = None
) -> list:
    """Get documents from a collection"""
    db = get_firestore()
    query = db.collection(collection)

    # Apply filters
    if filters:
        for field, op, value in filters:
            query = query.where(field, op, value)

    # Apply ordering
    if order_by:
        direction = firestore.Query.DESCENDING if order_direction == 'DESCENDING' else firestore.Query.ASCENDING
        query = query.order_by(order_by, direction=direction)

    # Apply limit
    query = query.limit(limit)

    docs = query.stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        results.append(data)

    return results


async def create_document(collection: str, data: dict, doc_id: str = None) -> str:
    """Create a new document in Firestore"""
    db = get_firestore()
    if doc_id:
        db.collection(collection).document(doc_id).set(data)
        return doc_id
    else:
        doc_ref = db.collection(collection).add(data)
        return doc_ref[1].id


async def update_document(collection: str, doc_id: str, data: dict) -> bool:
    """Update a document in Firestore"""
    db = get_firestore()
    db.collection(collection).document(doc_id).update(data)
    return True


async def set_document(collection: str, doc_id: str, data: dict) -> bool:
    """Set a document in Firestore (creates or overwrites)"""
    db = get_firestore()
    db.collection(collection).document(doc_id).set(data)
    return True


async def delete_document(collection: str, doc_id: str) -> bool:
    """Delete a document from Firestore"""
    db = get_firestore()
    db.collection(collection).document(doc_id).delete()
    return True


async def get_subcollection(
    collection: str,
    doc_id: str,
    subcollection: str,
    limit: int = 100,
    order_by: str = None
) -> list:
    """Get documents from a subcollection"""
    db = get_firestore()
    query = db.collection(collection).document(doc_id).collection(subcollection)

    if order_by:
        query = query.order_by(order_by)

    query = query.limit(limit)

    docs = query.stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        results.append(data)

    return results


async def get_collection_count(collection: str) -> int:
    """Get the count of documents in a collection"""
    db = get_firestore()
    # Note: For large collections, consider using a counter document
    docs = db.collection(collection).stream()
    return sum(1 for _ in docs)


async def upload_file(
    file_content: bytes,
    destination_path: str,
    content_type: str = "application/octet-stream"
) -> str:
    """
    Upload a file to Firebase Storage

    Args:
        file_content: File content as bytes
        destination_path: Path in storage bucket (e.g., "podcasts/audio_123.mp3")
        content_type: MIME type of the file

    Returns:
        Public URL of the uploaded file
    """
    bucket = get_storage()
    blob = bucket.blob(destination_path)

    # Upload the file
    blob.upload_from_string(file_content, content_type=content_type)

    # Make the file publicly accessible
    blob.make_public()

    return blob.public_url
