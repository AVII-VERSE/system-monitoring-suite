"""
===================================================================
Project: Advanced Keylogger Suite - Decryption Utility
Author: Avi
Date: 2026
Description: Utility to decrypt AES-Fernet encrypted log files.
===================================================================
"""

import os
from cryptography.fernet import Fernet

def decrypt_logs(key_path="encryption_key.txt", log_dir="../logs"):
    if not os.path.exists(key_path):
        print(f"[!] Encryption key file not found: {key_path}")
        return

    with open(key_path, "rb") as kf:
        key = kf.read().strip()

    fernet = Fernet(key)
    encrypted_files = ["enc_key_log.txt", "enc_systeminfo.txt", "enc_clipboard.txt"]

    for enc_fname in encrypted_files:
        enc_fpath = os.path.join(log_dir, enc_fname)
        if os.path.exists(enc_fpath):
            try:
                with open(enc_fpath, "rb") as ef:
                    enc_data = ef.read()
                
                dec_data = fernet.decrypt(enc_data)
                dec_fname = "decrypted_" + enc_fname.replace("enc_", "")
                dec_fpath = os.path.join(log_dir, dec_fname)

                with open(dec_fpath, "wb") as df:
                    df.write(dec_data)
                
                print(f"[+] Decrypted {enc_fname} -> {dec_fname}")
            except Exception as e:
                print(f"[!] Failed to decrypt {enc_fname}: {e}")

if __name__ == "__main__":
    decrypt_logs()
