# generate_all_openssl.py
import subprocess, os

os.makedirs("keys", exist_ok=True)
os.makedirs("data", exist_ok=True)

steps = [
    ("Create unsigned certificate", "python create_unsigned_cert.py"),
    ("Canonicalize JSON", "python canonicalize.py"),
    ("Sign canonical JSON (OpenSSL)", "openssl dgst -sha256 -sign keys/private.pem -out data/sig.bin data/cert_canonical.json"),
    ("Embed signature", "python embed_signature.py"),
    ("Generate PDF", "python make_pdf.py"),
    ("Verify signature (OpenSSL)", "openssl dgst -sha256 -verify keys/public.pem -signature data/sig.bin data/cert_canonical.json"),
]

for desc, cmd in steps:
    print("\n>>", desc)
    rc = subprocess.call(cmd, shell=True)
    if rc != 0:
        print("Error running:", cmd)
        break
