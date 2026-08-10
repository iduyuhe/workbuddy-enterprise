"""国密算法单元测试（密评能力验证）。

运行：
    python -m pytest src/shared/crypto/tests/test_sm.py -q
或：
    python src/shared/crypto/tests/test_sm.py
"""

import base64
import os
import sys

# 让 shared 包可被导入（脚本直跑时用）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from shared.crypto import (
    SM2KeyPair,
    generate_keypair,
    sm3_hex,
    sm4_decrypt,
    sm4_encrypt,
    sm4_decrypt_str,
    sm4_encrypt_str,
    system_sm2,
)


def test_sm3_known_vector():
    # GB/T 32905 标准测试向量
    assert sm3_hex(b"abc") == (
        "66c7f0f462eeedd9d1f2d46bdc10e4e24167c4875cf2f7a2297da02b8f4ba8e0"
    )
    assert sm3_hex(b"") == (
        "1ab21d8355cfa17f8e61194831e81a8f22bec8c728fefb747ed035eb5082aa2b"
    )


def test_sm4_cbc_roundtrip():
    key = b"0123456789ABCDEF"  # 16 bytes
    pt = b"WorkBuddy Enterprise - sensitive payload!"
    blob = sm4_encrypt(key, pt)
    assert blob != pt
    assert sm4_decrypt(key, blob) == pt


def test_sm4_str_roundtrip():
    key = b"FEDCBA9876543210"
    s = "工业5点0产业生态联盟"
    b64 = sm4_encrypt_str(key, s)
    assert b64 != s
    assert sm4_decrypt_str(key, b64) == s
    # base64 可逆且不含原文
    raw = base64.b64decode(b64)
    assert s.encode("utf-8") not in raw


def test_sm2_keypair_sign_verify():
    kp = SM2KeyPair.generate()
    msg = b"commercial cipher application security assessment"
    sig = kp.sign(msg)
    assert len(sig) == 128
    assert kp.verify(sig, msg) is True
    # 篡改消息应验签失败
    assert kp.verify(sig, b"tampered") is False


def test_sm2_keypair_encrypt_decrypt():
    kp = SM2KeyPair.generate()
    secret = b"top-secret-config-value"
    enc = kp.encrypt(secret)
    assert enc != secret
    assert kp.decrypt(enc) == secret


def test_generate_keypair_returns_hex():
    priv, pub = generate_keypair()
    assert len(priv) == 64 and len(pub) == 128


def test_system_sm2_stable_within_process():
    a = system_sm2()
    b = system_sm2()
    assert a.private_key == b.private_key
    # 系统密钥可正常签名验签
    sig = a.sign(b"ping")
    assert a.verify(sig, b"ping")


def test_sm4_at_rest_in_sqlite():
    """演示：SM4 加密字段写入 SQLite，读回解密，落盘内容不含明文。"""
    import sqlite3
    import tempfile
    import os as _os

    key = b"atrestkey1234567"[:16]
    plaintext = "user-api-token-9f3c2a"

    db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db.close()
    try:
        conn = sqlite3.connect(db.name)
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, secret BLOB)")
        blob = sm4_encrypt(key, plaintext.encode("utf-8"))
        conn.execute("INSERT INTO t (secret) VALUES (?)", (blob,))
        conn.commit()
        row = conn.execute("SELECT secret FROM t WHERE id=1").fetchone()[0]
        conn.close()

        stored = bytes(row)
        assert plaintext.encode("utf-8") not in stored  # 落盘非明文
        assert sm4_decrypt(key, stored).decode("utf-8") == plaintext
    finally:
        _os.unlink(db.name)


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
