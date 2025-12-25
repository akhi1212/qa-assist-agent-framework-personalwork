"""
ChromaDB Utility for Jira Ticket Storage
----------------------------------------
Stores Jira ticket information (valid/invalid) in ChromaDB vector database.
"""
import os
import json
from datetime import datetime
import chromadb
from chromadb.config import Settings

# ChromaDB client and collection
_client = None
_collection = None

def get_chromadb_client():
    """Initialize and return ChromaDB client"""
    global _client
    if _client is None:
        # Create persistent client (data stored in ./chroma_db directory)
        _client = chromadb.PersistentClient(path="./chroma_db")
    return _client

def get_jira_tickets_collection():
    """Get or create the Jira tickets collection"""
    global _collection
    if _collection is None:
        client = get_chromadb_client()
        try:
            _collection = client.get_collection(name="jira_tickets")
        except:
            # Create collection if it doesn't exist
            _collection = client.create_collection(
                name="jira_tickets",
                metadata={"description": "Stores Jira ticket validation results"}
            )
    return _collection

def save_jira_ticket(ticket_id: str, ticket_key: str, description: str, is_valid: bool, 
                     jira_url: str = "", error_message: str = ""):
    """
    Save Jira ticket information to ChromaDB.
    
    Args:
        ticket_id: Jira ticket ID (e.g., "PROJ-123")
        ticket_key: Jira ticket key (e.g., "PROJ")
        description: Ticket description/summary
        is_valid: Whether the ticket is valid or not
        jira_url: Jira instance URL
        error_message: Error message if ticket is invalid
    """
    try:
        collection = get_jira_tickets_collection()
        
        # Create metadata
        metadata = {
            "ticket_id": ticket_id,
            "ticket_key": ticket_key,
            "is_valid": str(is_valid),
            "jira_url": jira_url,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat(),
            "description": description[:500]  # Limit description length
        }
        
        # Create document text (for embedding/search)
        document_text = f"""
        Jira Ticket: {ticket_id}
        Key: {ticket_key}
        Description: {description}
        Status: {'Valid' if is_valid else 'Invalid'}
        URL: {jira_url}
        Error: {error_message}
        """
        
        # Generate unique ID
        doc_id = f"{ticket_key}_{ticket_id}_{datetime.now().timestamp()}"
        
        # Add to collection
        collection.add(
            ids=[doc_id],
            documents=[document_text],
            metadatas=[metadata]
        )
        
        return True
    except Exception as e:
        print(f"Error saving to ChromaDB: {e}")
        return False

def get_jira_ticket_history(ticket_id: str = None, limit: int = 10):
    """
    Retrieve Jira ticket history from ChromaDB.
    
    Args:
        ticket_id: Optional ticket ID to filter by
        limit: Maximum number of results to return
        
    Returns:
        List of ticket records
    """
    try:
        collection = get_jira_tickets_collection()
        
        if ticket_id:
            # Query by ticket ID
            results = collection.get(
                where={"ticket_id": ticket_id},
                limit=limit
            )
        else:
            # Get recent tickets
            results = collection.get(limit=limit)
        
        tickets = []
        if results['ids']:
            for i, doc_id in enumerate(results['ids']):
                tickets.append({
                    "id": doc_id,
                    "metadata": results['metadatas'][i],
                    "document": results['documents'][i]
                })
        
        return tickets
    except Exception as e:
        print(f"Error retrieving from ChromaDB: {e}")
        return []

def search_jira_tickets(query: str, limit: int = 5):
    """
    Search Jira tickets by description or content.
    
    Args:
        query: Search query text
        limit: Maximum number of results
        
    Returns:
        List of matching tickets
    """
    try:
        collection = get_jira_tickets_collection()
        
        results = collection.query(
            query_texts=[query],
            n_results=limit
        )
        
        tickets = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i, doc_id in enumerate(results['ids'][0]):
                idx = i
                tickets.append({
                    "id": doc_id,
                    "metadata": results['metadatas'][0][idx],
                    "document": results['documents'][0][idx],
                    "distance": results['distances'][0][idx] if 'distances' in results else None
                })
        
        return tickets
    except Exception as e:
        print(f"Error searching ChromaDB: {e}")
        return []

