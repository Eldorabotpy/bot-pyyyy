import os
import json
import pymongo
from pprint import pformat

SENSITIVE_KEYS = {
    "password", "senha", "pass", "hash", "password_hash",
    "token", "access_token", "refresh_token", "session_token",
    "secret", "api_key", "key"
}

def _mask_sensitive(obj):
    """Mascara valores sensíveis sem remover as chaves."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if lk in SENSITIVE_KEYS or any(s in lk for s in ["token", "senha", "password", "secret", "key", "hash"]):
                out[k] = "***"
            else:
                out[k] = _mask_sensitive(v)
        return out
    if isinstance(obj, list):
        return [_mask_sensitive(x) for x in obj]
    return obj

def main():
    # Use variável de ambiente se possível:
    # set MONGO_URI=...
    MONGO_URI = os.getenv("MONGO_URI") or "mongodb+srv://eldora-cluster:pb060987@cluster0.4iqgjaf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    DB_NAME = os.getenv("DB_NAME") or "eldora_db"

    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")

    db = client[DB_NAME]
    colls = sorted(db.list_collection_names())

    lines = []
    lines.append(f"DB: {DB_NAME}")
    lines.append(f"Collections ({len(colls)}): {', '.join(colls)}")
    lines.append("")

    for c in colls:
        col = db[c]
        lines.append("=" * 80)
        lines.append(f"COLLECTION: {c}")
        lines.append("=" * 80)

        # Indexes
        try:
            indexes = col.index_information()
        except Exception as e:
            indexes = {"ERROR": str(e)}
        lines.append("INDEXES:")
        lines.append(pformat(indexes))

        # Sample docs
        try:
            docs = list(col.find({}).limit(2))
            docs = _mask_sensitive(docs)
        except Exception as e:
            docs = [{"ERROR": str(e)}]
        lines.append("\nSAMPLE_DOCS (limit 2):")
        lines.append(pformat(docs))
        lines.append("")

    out_path = "mongo_snapshot.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    client.close()
    print(f"OK: snapshot gerado em {out_path}")

if __name__ == "__main__":
    main()
