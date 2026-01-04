import hashlib
import json
from dataclasses import dataclass, asdict
from typing import List, Optional
from .bitcoin_integration import BitcoinKey

@dataclass
class VaultMember:
    """Represents a member of the multi-party vault"""
    pubkey: str  # Bitcoin public key (hex)
    share_percentage: int  # 0-100
    join_height: int  # Block height when joined
    
    def __post_init__(self):
        if not (0 <= self.share_percentage <= 100):
            raise ValueError("Share percentage must be between 0 and 100")

@dataclass
class Vault:
    """Core vault state that gets committed to Bitcoin UTXO"""
    members: List[VaultMember]
    total_balance: int  # satoshis
    created_height: int
    vault_id: str
    
    def __init__(self, members: List[VaultMember]):
        self.members = members
        self.total_balance = 0
        self.created_height = 0
        self.vault_id = self._generate_vault_id()
        
        # Validate member shares
        total_shares = sum(m.share_percentage for m in members)
        if total_shares != 100:
            raise ValueError(f"Member shares must sum to 100%, got {total_shares}%")
    
    def _generate_vault_id(self) -> str:
        """Generate deterministic vault ID from members"""
        hasher = hashlib.sha256()
        hasher.update(b"MULTIPARTY_VAULT_V1")
        
        for member in sorted(self.members, key=lambda m: m.pubkey):
            hasher.update(bytes.fromhex(member.pubkey))
        
        return hasher.hexdigest()
    
    def commitment_hash(self) -> str:
        """Generate commitment hash for Bitcoin UTXO"""
        hasher = hashlib.sha256()
        hasher.update(bytes.fromhex(self.vault_id))
        
        for member in self.members:
            hasher.update(bytes.fromhex(member.pubkey))
            hasher.update(member.share_percentage.to_bytes(1, 'little'))
            hasher.update(member.join_height.to_bytes(4, 'little'))
        
        hasher.update(self.total_balance.to_bytes(8, 'little'))
        hasher.update(self.created_height.to_bytes(4, 'little'))
        
        return hasher.hexdigest()
    
    def is_member(self, pubkey: str) -> bool:
        """Check if pubkey is a vault member"""
        return any(m.pubkey == pubkey for m in self.members)
    
    def get_member_share(self, pubkey: str) -> Optional[int]:
        """Get member's share percentage"""
        for member in self.members:
            if member.pubkey == pubkey:
                return member.share_percentage
        return None
    
    def to_dict(self) -> dict:
        """Serialize vault to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Vault':
        """Deserialize vault from dictionary"""
        members = [VaultMember(**m) for m in data['members']]
        vault = cls(members)
        vault.total_balance = data['total_balance']
        vault.created_height = data['created_height']
        vault.vault_id = data['vault_id']
        return vault

class MultiPartyVault:
    """High-level interface for multi-party vault operations"""
    
    def __init__(self, members: List[VaultMember], rules: 'WithdrawalRules'):
        self.vault = Vault(members)
        self.rules = rules
        self._withdrawal_history = []
    
    def create_withdrawal_proof(self, request: 'WithdrawalRequest') -> 'GrailProof':
        """Create zk proof for withdrawal using Grail Pro interface"""
        from .predicate import VaultPredicate
        from .bos_stack.grail_pro import GrailProof
        
        # Validate request first
        predicate = VaultPredicate(self.vault, self.rules, request)
        is_valid, reason = predicate.verify()
        if not is_valid:
            raise ValueError(f"Predicate verification failed: {reason}")
        
        return GrailProof.generate(predicate, self.vault)
    
    def verify_withdrawal(self, proof: 'GrailProof') -> bool:
        """Verify withdrawal proof"""
        return proof.verify(self.vault.commitment_hash())
    
    def execute_withdrawal(self, proof: 'GrailProof') -> dict:
        """Execute withdrawal if proof is valid"""
        if not self.verify_withdrawal(proof):
            raise ValueError("Invalid withdrawal proof")
        
        withdrawal_amount = proof.get_withdrawal_amount()
        
        if withdrawal_amount > self.vault.total_balance:
            raise ValueError("Insufficient vault balance")
        
        # Record withdrawal
        self.vault.total_balance -= withdrawal_amount
        self._withdrawal_history.append({
            'amount': withdrawal_amount,
            'height': proof.predicate.withdrawal_request.current_height,
            'signers': proof.predicate.withdrawal_request.signers,
            'timestamp': proof.predicate.withdrawal_request.current_height
        })
        
        return {
            'success': True,
            'withdrawal_amount': withdrawal_amount,
            'remaining_balance': self.vault.total_balance,
            'transaction_id': f"mock_tx_{hashlib.sha256(str(withdrawal_amount).encode()).hexdigest()[:16]}"
        }
    
    def get_withdrawal_history(self) -> List[dict]:
        """Get vault withdrawal history"""
        return self._withdrawal_history.copy()
    
    def create_governance_token(self) -> 'VaultToken':
        """Create Charms-compatible governance tokens"""
        from .bos_stack.charms import VaultToken
        return VaultToken.create_for_vault(self.vault)
