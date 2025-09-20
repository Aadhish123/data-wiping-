# embed_signature.py
import sys, json, base64, os

def embed(unsigned_path="data/unsigned_cert.json", sigbin="data/sig.bin", out="data/signed_cert.json"):
    with open(sigbin, "rb") as f:
        sig_b64 = base64.b64encode(f.read()).decode()
    cert = json.load(open(unsigned_path, "r", encoding="utf-8"))
    cert["sign"] = {"alg": "rsa-sha256", "sig": sig_b64, "pubkey_id": "trustwipe-openssl-1"}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(cert, f, indent=2, ensure_ascii=False)
    print("Signed certificate written to", out)

if __name__ == "__main__":
    embed()

