"""国密（GM/T）密码支撑包。

提供 SM2 / SM3 / SM4 三种国密算法的统一封装，作为「密评」（商用密码应用
安全性评估）的能力底座。实现依赖纯 Python 国密库 `gmssl`，可离线运行。

典型用途：
  - SM3：敏感数据杂凑（完整性校验、签名摘要）。
  - SM4：对称加密，用于敏感字段「加密存储」（等保数据保密性）。
  - SM2：非对称签名/验签（抗抵赖）、加密/解密（密钥交换、字段加密）。
"""

from .sm import (
    SM2KeyPair,
    generate_keypair,
    sm3_hex,
    sm4_decrypt,
    sm4_decrypt_str,
    sm4_encrypt,
    sm4_encrypt_str,
    system_sm2,
)

__all__ = [
    "sm3_hex",
    "sm4_encrypt",
    "sm4_decrypt",
    "sm4_encrypt_str",
    "sm4_decrypt_str",
    "SM2KeyPair",
    "generate_keypair",
    "system_sm2",
]
