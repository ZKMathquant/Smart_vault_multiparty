from dataclasses import dataclass
from typing import Optional

@dataclass
class WithdrawalRules:
    """Programmable withdrawal rules for the vault"""
    
    # Basic quorum rules
    min_signers: int
    large_withdrawal_threshold: int  # satoshis
    large_withdrawal_requires_all: bool
    
    # Penalty system
    early_withdrawal_penalty_bps: int  # basis points (1000 = 10%)
    penalty_free_height: int
    
    # Emergency and limits
    emergency_timeout_blocks: int
    max_single_withdrawal: int  # satoshis
    withdrawal_cooling_period: int  # blocks
    
    @classmethod
    def conservative(cls) -> 'WithdrawalRules':
        """Create conservative withdrawal rules"""
        return cls(
            min_signers=2,
            large_withdrawal_threshold=10_000_000,  # 0.1 BTC
            large_withdrawal_requires_all=True,
            early_withdrawal_penalty_bps=1000,  # 10%
            penalty_free_height=0,  # Set when vault created
            emergency_timeout_blocks=52560,  # ~1 year
            max_single_withdrawal=100_000_000,  # 1 BTC
            withdrawal_cooling_period=144  # ~1 day
        )
    
    @classmethod
    def permissive(cls) -> 'WithdrawalRules':
        """Create permissive withdrawal rules"""
        return cls(
            min_signers=1,
            large_withdrawal_threshold=50_000_000,  # 0.5 BTC
            large_withdrawal_requires_all=False,
            early_withdrawal_penalty_bps=500,  # 5%
            penalty_free_height=0,
            emergency_timeout_blocks=26280,  # ~6 months
            max_single_withdrawal=200_000_000,  # 2 BTC
            withdrawal_cooling_period=72  # ~12 hours
        )
    
    def calculate_penalty(self, amount: int, current_height: int) -> int:
        """Calculate penalty for early withdrawal"""
        if current_height >= self.penalty_free_height:
            return 0
        
        return (amount * self.early_withdrawal_penalty_bps) // 10_000
    
    def is_large_withdrawal(self, amount: int) -> bool:
        """Check if withdrawal is considered large"""
        return amount >= self.large_withdrawal_threshold
    
    def validate_withdrawal(self, amount: int, signers_count: int, total_members: int) -> tuple[bool, str]:
        """Validate withdrawal against rules"""
        
        # Check minimum signers
        if signers_count < self.min_signers:
            return False, f"Need at least {self.min_signers} signers, got {signers_count}"
        
        # Check large withdrawal rules
        if self.is_large_withdrawal(amount) and self.large_withdrawal_requires_all:
            if signers_count != total_members:
                return False, f"Large withdrawal requires all {total_members} signers, got {signers_count}"
        
        # Check maximum withdrawal limit
        if amount > self.max_single_withdrawal:
            return False, f"Withdrawal {amount} exceeds maximum {self.max_single_withdrawal}"
        
        return True, "Valid withdrawal"
    
    def check_cooling_period(self, current_height: int, last_withdrawal_height: Optional[int], amount: int) -> tuple[bool, str]:
        """Check if cooling period has passed for large withdrawals"""
        if not self.is_large_withdrawal(amount):
            return True, "No cooling period for small withdrawals"
        
        if last_withdrawal_height is None:
            return True, "No previous withdrawals"
        
        blocks_since_last = current_height - last_withdrawal_height
        if blocks_since_last < self.withdrawal_cooling_period:
            remaining = self.withdrawal_cooling_period - blocks_since_last
            return False, f"Cooling period: {remaining} blocks remaining"
        
        return True, "Cooling period satisfied"
