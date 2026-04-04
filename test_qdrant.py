"""Quick connectivity check for self-hosted Qdrant."""

from qdrant_client import QdrantClient
from production_rag.config import qdrant

def main():
    url = qdrant.url
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    if ":443" not in url:
        url = f"{url}:443"

    print(f"Connecting to {url} ...")
    client = QdrantClient(url=url, api_key=qdrant.api_key or None, prefer_grpc=False)

    # Basic health check
    info = client.get_collections()
    print(f"Connected! Found {len(info.collections)} collection(s):")
    for c in info.collections:
        print(f"  - {c.name}")

    # If a collection is configured, check it specifically
    if qdrant.collection_name:
        col = client.get_collection(qdrant.collection_name)
        print(f"\nCollection '{qdrant.collection_name}':")
        print(f"  Points:  {col.points_count}")
        print(f"  Vectors: {col.vectors_count}")
        print(f"  Status:  {col.status}")

if __name__ == "__main__":
    main()
