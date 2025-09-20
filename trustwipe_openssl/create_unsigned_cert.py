# create_unsigned_cert.py
import os, json, hashlib, datetime, secrets

def sha256_hex(b):
    import hashlib
    return hashlib.sha256(b).hexdigest()

def build_unsigned_cert(device_serial="DEVICE-1234", testfile="data/testfile.bin"):
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(testfile):
        with open(testfile, "wb") as f:
            f.write(b"A" * 4096)

    start = datetime.datetime.utcnow().isoformat() + "Z"

    length = os.path.getsize(testfile)
    # demo overwrite (simulate wipe) - DO NOT use on real devices as a substitute for secure erase
    with open(testfile, "r+b") as f:
        f.seek(0)
        f.write(secrets.token_bytes(length))
        f.flush()
        os.fsync(f.fileno())

    samples = []
    for offset in (0, max(0, length//2), max(0, length-512)):
        with open(testfile, "rb") as f:
            f.seek(offset)
            data = f.read(min(512, length))
            samples.append({"offset": offset, "hash": "sha256$"+sha256_hex(data)})

    finished = datetime.datetime.utcnow().isoformat() + "Z"

    cert = {
        "schema": "org.trustwipe.cert.v1",
        "device": {
            "class": "demo-file",
            "serial_hash": "sha256$" + sha256_hex(device_serial.encode()),
            "capacity_bytes": length
        },
        "wipe": {
            "action": "purge",
            "method": "demo_overwrite",
            "started_at": start,
            "finished_at": finished,
            "result": "success"
        },
        "evidence": {"samples": samples},
        "meta": {"tool_version": "trustwipe-openssl-demo-0.1"}
    }
    return cert

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    cert = build_unsigned_cert()
    with open("data/unsigned_cert.json", "w", encoding="utf-8") as f:
        json.dump(cert, f, indent=2, ensure_ascii=False)
    print("Unsigned certificate written to data/unsigned_cert.json")

