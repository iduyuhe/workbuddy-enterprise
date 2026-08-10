"""国密（GM/T）算法封装。

依赖 `gmssl`（纯 Python 国密实现）。本模块对 gmssl 的底层 API 做了工程化
封装，屏蔽以下易错点：
  - SM2 签名/验签的 `data` 必须是「消息的 SM3 杂凑值（bytes）」而非原文；
  - SM2 随机数 K 必须落在曲线阶 n 之内（否则签名非法、验签失败）；
  - SM2 密钥对需与当前 gmssl 版本的曲线参数一致（示例密钥常因版本漂移失配），
    因此提供 `generate_keypair()` 运行时生成真正匹配的密钥对。
"""

from __future__ import annotations

import os
import secrets
from typing import Optional

from gmssl import sm2, sm3, sm4


# ---------------------------------------------------------------------------
# SM3 杂凑
# ---------------------------------------------------------------------------
def sm3_hex(data: bytes) -> str:
    """返回 data 的 SM3 杂凑值（64 位十六进制字符串）。

    SM3('abc') = 66c7f0f462eeedd9d1f2d46bdc10e4e24167c4875cf2f7a2297da02b8f4ba8e0
    """
    return sm3.sm3_hash(list(data))


# ---------------------------------------------------------------------------
# SM4 对称加密（CBC 模式，随机 IV 前置）
# ---------------------------------------------------------------------------
_SM4_BLOCK = 16
_SM4_IV_LEN = 16


def _pkcs7_pad(data: bytes, block: int = _SM4_BLOCK) -> bytes:
    pad = block - (len(data) % block)
    return data + bytes([pad]) * pad


def _pkcs7_unpad(data: bytes) -> bytes:
    pad = data[-1]
    if pad < 1 or pad > _SM4_BLOCK:
        raise ValueError("invalid SM4 padding")
    return data[:-pad]


def sm4_encrypt(key: bytes, plaintext: bytes) -> bytes:
    """SM4-CBC 加密，返回 `IV(16) || ciphertext`，密钥须 16 字节。"""
    if len(key) != _SM4_BLOCK:
        raise ValueError("SM4 key must be 16 bytes")
    iv = secrets.token_bytes(_SM4_IV_LEN)
    crypt = sm4.CryptSM4()
    crypt.set_key(key, sm4.SM4_ENCRYPT)
    ct = crypt.crypt_cbc(iv, _pkcs7_pad(plaintext))
    return iv + ct


def sm4_decrypt(key: bytes, blob: bytes) -> bytes:
    """解密 `sm4_encrypt` 产出的 `IV || ciphertext`，返回明文。"""
    if len(key) != _SM4_BLOCK:
        raise ValueError("SM4 key must be 16 bytes")
    if len(blob) < _SM4_IV_LEN + _SM4_BLOCK:
        raise ValueError("SM4 blob too short")
    iv, ct = blob[:_SM4_IV_LEN], blob[_SM4_IV_LEN:]
    crypt = sm4.CryptSM4()
    crypt.set_key(key, sm4.SM4_DECRYPT)
    pt = crypt.crypt_cbc(iv, ct)
    return _pkcs7_unpad(pt)


def sm4_encrypt_str(key: bytes, text: str) -> str:
    """字符串便捷封装：加密后返回 base64 字符串。"""
    import base64

    return base64.b64encode(sm4_encrypt(key, text.encode("utf-8"))).decode("ascii")


def sm4_decrypt_str(key: bytes, b64: str) -> str:
    import base64

    return sm4_decrypt(key, base64.b64decode(b64)).decode("utf-8")


# ---------------------------------------------------------------------------
# SM2 非对称
# ---------------------------------------------------------------------------
class SM2KeyPair:
    """SM2 密钥对封装：签名/验签 + 加密/解密。

    `sign` / `verify` 遵循国密规范——对消息先做 SM3 杂凑，再对杂凑值签名。
    """

    def __init__(self, private_key: str, public_key: str):
        if not private_key or not public_key:
            raise ValueError("SM2KeyPair requires both private and public hex keys")
        self.private_key = private_key
        self.public_key = public_key
        self._c = sm2.CryptSM2(public_key=public_key, private_key=private_key)

    @classmethod
    def generate(cls) -> "SM2KeyPair":
        """生成一对真正匹配当前 gmssl 曲线参数的 SM2 密钥。"""
        tmp = sm2.CryptSM2(public_key="", private_key="")
        n = int(tmp.ecc_table["n"], 16)
        d = secrets.randbelow(n - 2) + 1
        d_hex = format(d, "064x")
        pub_hex = tmp._kg(d, tmp.ecc_table["g"])  # "x||y" hex
        return cls(private_key=d_hex, public_key=pub_hex)

    def sign(self, message: bytes) -> str:
        """对 message 签名，返回 r||s 的 128 位十六进制字符串。"""
        digest = bytes.fromhex(sm3_hex(message))
        n = int(self._c.ecc_table["n"], 16)
        # K 须落在 [1, n-1]，用 31 字节随机数确保 < n（n 略小于 2^256）
        for _ in range(8):
            k = secrets.randbelow(n - 2) + 1
            k_hex = format(k, "064x")
            sig = self._c.sign(digest, k_hex)
            if sig:
                return sig
        raise RuntimeError("SM2 sign failed after retries")

    def verify(self, signature: str, message: bytes) -> bool:
        digest = bytes.fromhex(sm3_hex(message))
        return bool(self._c.verify(signature, digest))

    def encrypt(self, message: bytes) -> bytes:
        return self._c.encrypt(message)

    def decrypt(self, ciphertext: bytes) -> bytes:
        return self._c.decrypt(ciphertext)

    def to_dict(self) -> dict:
        return {"private_key": self.private_key, "public_key": self.public_key}

    @classmethod
    def from_dict(cls, d: dict) -> "SM2KeyPair":
        return cls(private_key=d["private_key"], public_key=d["public_key"])


def generate_keypair() -> tuple[str, str]:
    """返回 (private_hex, public_hex)。"""
    kp = SM2KeyPair.generate()
    return kp.private_key, kp.public_key


# ---------------------------------------------------------------------------
# 进程级系统 SM2 密钥（env 注入或首次启动生成并缓存）
# 用于平台级签名（如审计日志抗抵赖、票据签名）。
# ---------------------------------------------------------------------------
_SYSTEM_SM2: Optional[SM2KeyPair] = None


def system_sm2() -> SM2KeyPair:
    """返回进程级 SM2 密钥。

    优先级：环境变量 SM2_PRIVATE_KEY / SM2_PUBLIC_KEY > 首次调用时生成并缓存。
    生成式密钥在进程重启后会变化，仅适合 DEV/演示；生产须由 env 注入固定密钥。
    """
    global _SYSTEM_SM2
    if _SYSTEM_SM2 is not None:
        return _SYSTEM_SM2
    priv = os.getenv("SM2_PRIVATE_KEY")
    pub = os.getenv("SM2_PUBLIC_KEY")
    if priv and pub:
        _SYSTEM_SM2 = SM2KeyPair(private_key=priv, public_key=pub)
    else:
        _SYSTEM_SM2 = SM2KeyPair.generate()
    return _SYSTEM_SM2
