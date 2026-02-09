from cryptography import x509
from cryptography.hazmat.primitives import serialization
import os

# Load PFX file
with open('cert.pfx', 'rb') as f:
    pfx_data = f.read()

# Extract certificate and private key
private_key, certificate, additional_certificates = serialization.pkcs12.load_key_and_certificates(
    pfx_data,
    b'connectly'  # password used during export
)

# Save certificate
with open('cert.pem', 'wb') as f:
    f.write(certificate.public_bytes(serialization.Encoding.PEM))

# Save private key
with open('key.pem', 'wb') as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))

print("✓ Certificate converted to PEM format!")
print("Files created: cert.pem, key.pem")