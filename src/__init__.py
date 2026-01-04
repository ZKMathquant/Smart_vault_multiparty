"""
Multi-Party Smart Vault - Bitcoin programmable custody
Using BitcoinOS-aligned interfaces implemented in Python
"""

from .vault import Vault, VaultMember, MultiPartyVault
from .rules import WithdrawalRules
from .predicate import VaultPredicate, WithdrawalRequest

__version__ = "0.1.0"
__all__ = [
    "Vault", 
    "VaultMember", 
    "MultiPartyVault",
    "WithdrawalRules",
    "VaultPredicate", 
    "WithdrawalRequest"
]
