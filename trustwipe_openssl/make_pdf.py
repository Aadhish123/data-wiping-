# make_pdf.py
import os, json, hashlib, qrcode
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

os.makedirs("data", exist_ok=True)
with open("data/signed_cert.json", "r", encoding="utf-8") as f:
    cert = json.load(f)

# prefer canonical bytes for hash
canon_path = "data/cert_canonical.json"
if os.path.exists(canon_path):
    with open(canon_path, "rb") as f:
        canon_bytes = f.read()
else:
    canon_bytes = json.dumps(cert, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

cert_hash = hashlib.sha256(canon_bytes).hexdigest()

qr = qrcode.make(cert_hash)
qr.save("data/cert_qr.png")

pdf_file = "data/certificate.pdf"
c = canvas.Canvas(pdf_file, pagesize=A4)
width, height = A4

c.setFont("Helvetica-Bold", 18)
c.drawCentredString(width/2, height - 80, "Secure Wipe Certificate")
c.line(60, height-90, width-60, height-90)

c.setFont("Helvetica", 11)
x_left = 70
y = height - 120

device = cert.get("device", {})
wipe = cert.get("wipe", {})
sign = cert.get("sign", {})

lines = [
    f"Device class: {device.get('class','N/A')}",
    f"Capacity (bytes): {device.get('capacity_bytes','N/A')}",
    f"Result: {wipe.get('result','N/A')}",
    f"Method: {wipe.get('method','N/A')}",
    f"Started: {wipe.get('started_at','N/A')}",
    f"Finished: {wipe.get('finished_at','N/A')}",
    f"Signer ID: {sign.get('pubkey_id','N/A')}"
]

for ln in lines:
    c.drawString(x_left, y, ln)
    y -= 16

c.drawString(x_left, y-8, f"Signature (first 64 chars): {sign.get('sig','')[:64]}")
c.drawString(x_left, y-28, f"Certificate SHA256: {cert_hash}")

qr_size = 2.0*inch
c.drawImage("data/cert_qr.png", width - (qr_size + 70), 120, qr_size, qr_size)

c.setFont("Helvetica-Oblique", 9)
c.drawCentredString(width/2, 50, "Verify with OpenSSL: openssl dgst -sha256 -verify keys/public.pem -signature data/sig.bin data/cert_canonical.json")
c.save()

print("PDF generated at data/certificate.pdf")


