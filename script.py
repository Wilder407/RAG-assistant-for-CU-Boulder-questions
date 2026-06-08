import chromadb
client = chromadb.PersistentClient(path="/Users/Lisa/Desktop/AI201_Repos/ai201-project1-unofficial-guide-starter/chroma_db")
col = client.get_collection("cu_boulder_guide")
results = col.get(include=["documents", "metadatas"])
for doc, meta in zip(results["documents"], results["metadatas"]):
    if "Trumbo" in meta.get("place_name", "") or "Dalton" in doc:
        print(meta["place_name"], "|", meta["chunk_index"])
        print(doc[:300])
        print()