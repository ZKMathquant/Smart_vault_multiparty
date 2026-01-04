from dataclasses import dataclass
from typing import List, Optional

@dataclass
class WithdrawalRequest:
    """Request for vault withdrawal"""
    amount: int  # satoshis
    current_height: int
    signers: List[str]  # List of public keys (hex)
    is_emergency: bool
    last_withdrawal_height: Optional[int] = None
    recipient_address: Optional[str] = None

class VaultPredicate:
    """zk predicate that enforces vault withdrawal rules"""
    
    def __init__(self, vault, rules, withdrawal_request: WithdrawalRequest):
        self.vault_commitment = vault.commitment_hash()
        self.rules = rules
        self.withdrawal_request = withdrawal_request
        self.vault = vault  # Keep reference for verification
    
    def verify(self) -> tuple[bool, str]:
        """
        Core predicate logic - this would run in Grail Pro zkVM
        Returns (is_valid, reason)
        """
        
        # Verify vault commitment matches
        if self.vault_commitment != self.vault.commitment_hash():
            return False, "Vault commitment mismatch"
        
        req = self.withdrawal_request
        
        # Verify all signers are vault members
        for signer in req.signers:
            if not self.vault.is_member(signer):
                return False, f"Signer {signer[:8]}... is not a vault member"
        
        # Remove duplicate signers
        unique_signers = list(set(req.signers))
        if len(unique_signers) != len(req.signers):
            return False, "Duplicate signers not allowed"
        
        # Emergency withdrawal path
        if req.is_emergency:
            blocks_since_creation = req.current_height - self.vault.created_height
            if blocks_since_creation >= self.rules.emergency_timeout_blocks:
                if len(unique_signers) >= 2:  # Require 2 signers for emergency
                    return True, "Emergency withdrawal approved"
                else:
                    return False, "Emergency withdrawal needs at least 2 signers"
            else:
                remaining = self.rules.emergency_timeout_blocks - blocks_since_creation
                return False, f"Emergency timeout not reached: {remaining} blocks remaining"
        
        # Normal withdrawal validation
        is_valid, reason = self.rules.validate_withdrawal(
            req.amount, 
            len(unique_signers), 
            len(self.vault.members)
        )
        if not is_valid:
            return False, reason
        
        # Check cooling period for large withdrawals
        cooling_ok, cooling_reason = self.rules.check_cooling_period(
            req.current_height,
            req.last_withdrawal_height,
            req.amount
        )
        if not cooling_ok:
            return False, cooling_reason
        
        # Ensure vault has sufficient balance
        penalty = self.rules.calculate_penalty(req.amount, req.current_height)
        net_withdrawal = req.amount - penalty
        
        if net_withdrawal > self.vault.total_balance:
            return False, f"Insufficient balance: need {net_withdrawal}, have {self.vault.total_balance}"
        
        return True, "Withdrawal approved"
    
    def get_net_withdrawal_amount(self) -> int:
        """Calculate net withdrawal amount after penalties"""
        penalty = self.rules.calculate_penalty(
            self.withdrawal_request.amount,
            self.withdrawal_request.current_height
        )
        return self.withdrawal_request.amount - penalty
    
    def get_penalty_amount(self) -> int:
        """Calculate penalty amount"""
        return self.rules.calculate_penalty(
            self.withdrawal_request.amount,
            self.withdrawal_request.current_height
        )
    
    def to_dict(self) -> dict:
        """Serialize predicate for proof generation"""
        return {
            'vault_commitment': self.vault_commitment,
            'rules': self.rules.__dict__,
            'withdrawal_request': {
                'amount': self.withdrawal_request.amount,
                'current_height': self.withdrawal_request.current_height,
                'signers': self.withdrawal_request.signers,
                'is_emergency': self.withdrawal_request.is_emergency,
                'last_withdrawal_height': self.withdrawal_request.last_withdrawal_height,
                'recipient_address': self.withdrawal_request.recipient_address
            }
        }
