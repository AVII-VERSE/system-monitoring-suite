"""
===================================================================
Project: Advanced Keylogger Suite - Key Generator
Author: Avi
Date: 2026
Description: Utility to generate AES-256 Fernet encryption key.
===================================================================
"""

from cryptography.fernet import Fernet

def generate_key():
    key = Fernet.generate_key()
    with open("encryption_key.txt", "wb") as f:
        f.write(key)
    print("[+] Generated encryption_key.txt successfully.")

if __name__ == "__main__":
    generate_key()
