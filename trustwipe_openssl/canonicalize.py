# canonicalize.py
import json, os

def canonicalize(input_path="data/unsigned_cert.json", output_path="data/cert_canonical.json"):
    obj = json.load(open(input_path, "r", encoding="utf-8"))
    with open(output_path, "wb") as f:
        f.write(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    canonicalize()
    print("Canonical JSON written to data/cert_canonical.json")

