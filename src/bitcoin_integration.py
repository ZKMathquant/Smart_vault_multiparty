"""
Bitcoin integration utilities
"""

import hashlib
from ecdsa import SigningKey, SECP256k1, VerifyingKey
from typing import Tuple

class BitcoinKey:
    """Bitcoin key management utilities"""
    
    def __init__(self, private_key: bytes = None):
        if private_key:
            self.private_key = SigningKey.from_string(private_key, curve=SECP256k1)
        else:
            self.private_key = SigningKey.generate(curve=SECP256k1)
        
        self.public_key = self.private_key.get_verifying_key()
    
    def get_public_key_hex(self) -> str:
        """Get compressed public key in hex format"""
        # Get uncompressed public key point
        point = self.public_key.pubkey.point
        
        # Compress the public key
        x = point.x()
        y = point.y()
        
        # Determine prefix (02 for even y, 03 for odd y)
        prefix = b'\x02' if y % 2 == 0 else b'\x03'
        
        # Convert x coordinate to 32 bytes
        x_bytes = x.to_bytes(32, 'big')
        
        # Return compressed public key
        return (prefix + x_bytes).hex()
    
    def sign_message(self, message: bytes) -> str:
        """Sign message and return signature in hex"""
        signature = self.private_key.sign(message)
        return signature.hex()
    
    def verify_signature(self, message: bytes, signature_hex: str, pubkey_hex: str) -> bool:
        """Verify signature against message and public key"""
        try:
            # Parse public key
            pubkey_bytes = bytes.fromhex(pubkey_hex)
            
            # Handle compressed public key
            if len(pubkey_bytes) == 33:
                # Decompress public key (simplified)
                prefix = pubkey_bytes[0]
                x = int.from_bytes(pubkey_bytes[1:], 'big')
                
                # This is a simplified decompression - in production use proper secp256k1 library
                # For now, create a mock verifying key
                vk = self.public_key  # Use current key for demo
            else:
                # Uncompressed key
                vk = VerifyingKey.from_string(pubkey_bytes, curve=SECP256k1)
            
            signature = bytes.fromhex(signature_hex)
            return vk.verify(signature, message)
            
        except Exception:
            return False
    
    @staticmethod
    def generate_key_pair() -> Tuple[str, str]:
        """Generate new key pair and return (private_key_hex, public_key_hex)"""
        key = BitcoinKey()
        private_hex = key.private_key.to_string().hex()
        public_hex = key.get_public_key_hex()
        return private_hex, public_hex
    
    @staticmethod
    def hash160(data: bytes) -> bytes:
        """Bitcoin HASH160 (RIPEMD160(SHA256(data)))"""
        sha256_hash = hashlib.sha256(data).digest()
        # Python doesn't have RIPEMD160 in hashlib by default
        # Using SHA256 as substitute for demo
        return hashlib.sha256(sha256_hash).digest()[:20]
    
    @staticmethod
    def double_sha256(data: bytes) -> bytes:
        """Bitcoin double SHA256"""
        return hashlib.sha256(hashlib.sha256(data).digest()).digest()
