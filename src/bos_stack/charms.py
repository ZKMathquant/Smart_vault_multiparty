"""
Charms - Programmable token standard (Python implementation)
BOS-aligned interface for vault governance and tokenization
"""

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from enum import Enum

class ProposalType(Enum):
    CHANGE_WITHDRAWAL_RULES = "change_withdrawal_rules"
    ADD_MEMBER = "add_member"
    REMOVE_MEMBER = "remove_member"
    EMERGENCY_EXIT = "emergency_exit"
    UPGRADE_VAULT = "upgrade_vault"

class ProposalStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PASSED = "passed"
    REJECTED = "rejected"
    EXECUTED = "executed"

@dataclass
class TokenMetadata:
    """Charms token metadata"""
    name: str
    symbol: str
    decimals: int
    vault_type: str
    description: str

@dataclass
class TokenAllocation:
    """Token allocation to vault member"""
    recipient: str  # public key
    amount: int
    share_percentage: int

class VaultToken:
    """Charms-compatible token representing vault shares"""
    
    def __init__(self, vault_id: str, total_supply: int, metadata: TokenMetadata):
        self.vault_id = vault_id
        self.total_supply = total_supply
        self.metadata = metadata
        self._balances = {}  # pubkey -> balance
        self._allowances = {}  # owner -> spender -> amount
        self._transfer_history = []
    
    @classmethod
    def create_for_vault(cls, vault: 'Vault') -> 'VaultToken':
        """Create Charms token for vault governance"""
        
        metadata = TokenMetadata(
            name=f"Vault Share Token {vault.vault_id[:8]}",
            symbol=f"VST{vault.vault_id[:4].upper()}",
            decimals=8,
            vault_type="MultiPartyVault",
            description=f"Governance token for multi-party vault {vault.vault_id}"
        )
        
        # 100M tokens = 100% of vault
        total_supply = 100_000_000
        
        token = cls(vault.vault_id, total_supply, metadata)
        token._mint_initial_tokens(vault)
        
        return token
    
    def _mint_initial_tokens(self, vault: 'Vault') -> List[TokenAllocation]:
        """Mint initial tokens to vault members"""
        
        allocations = []
        
        for member in vault.members:
            token_amount = (self.total_supply * member.share_percentage) // 100
            self._balances[member.pubkey] = token_amount
            
            allocation = TokenAllocation(
                recipient=member.pubkey,
                amount=token_amount,
                share_percentage=member.share_percentage
            )
            allocations.append(allocation)
        
        return allocations
    
    def balance_of(self, pubkey: str) -> int:
        """Get token balance for address"""
        return self._balances.get(pubkey, 0)
    
    def transfer(self, from_pubkey: str, to_pubkey: str, amount: int) -> bool:
        """Transfer tokens between addresses"""
        
        if amount <= 0:
            return False
        
        from_balance = self.balance_of(from_pubkey)
        if from_balance < amount:
            return False
        
        # Execute transfer
        self._balances[from_pubkey] = from_balance - amount
        self._balances[to_pubkey] = self.balance_of(to_pubkey) + amount
        
        # Record transfer
        self._transfer_history.append({
            'from': from_pubkey,
            'to': to_pubkey,
            'amount': amount,
            'timestamp': len(self._transfer_history)  # Mock timestamp
        })
        
        return True
    
    def approve(self, owner: str, spender: str, amount: int) -> bool:
        """Approve spender to transfer tokens on behalf of owner"""
        
        if owner not in self._allowances:
            self._allowances[owner] = {}
        
        self._allowances[owner][spender] = amount
        return True
    
    def allowance(self, owner: str, spender: str) -> int:
        """Get approved allowance"""
        return self._allowances.get(owner, {}).get(spender, 0)
    
    def transfer_from(self, spender: str, from_pubkey: str, to_pubkey: str, amount: int) -> bool:
        """Transfer tokens using allowance"""
        
        allowed = self.allowance(from_pubkey, spender)
        if allowed < amount:
            return False
        
        if not self.transfer(from_pubkey, to_pubkey, amount):
            return False
        
        # Reduce allowance
        self._allowances[from_pubkey][spender] = allowed - amount
        return True
    
    def get_voting_power(self, pubkey: str) -> float:
        """Get voting power percentage for address"""
        balance = self.balance_of(pubkey)
        return (balance / self.total_supply) * 100
    
    def get_transfer_history(self) -> List[Dict[str, Any]]:
        """Get token transfer history"""
        return self._transfer_history.copy()

@dataclass
class GovernanceProposal:
    """Governance proposal for vault management"""
    
    proposal_id: str
    proposer: str  # public key
    proposal_type: ProposalType
    title: str
    description: str
    
    # Voting parameters
    required_voting_power: float  # percentage (0-100)
    voting_period_blocks: int
    execution_delay_blocks: int
    
    # Proposal data
    proposal_data: Dict[str, Any]
    
    # State
    status: ProposalStatus
    votes_for: int
    votes_against: int
    voters: List[str]
    
    created_at_height: int
    voting_ends_at_height: int
    execution_height: Optional[int] = None

class GovernanceSystem:
    """Charms-based governance system for vault management"""
    
    def __init__(self, vault_token: VaultToken, vault: 'Vault'):
        self.vault_token = vault_token
        self.vault = vault
        self.proposals = {}  # proposal_id -> GovernanceProposal
        self._proposal_counter = 0
    
    def create_proposal(
        self,
        proposer: str,
        proposal_type: ProposalType,
        title: str,
        description: str,
        proposal_data: Dict[str, Any],
        current_height: int,
        required_voting_power: float = 51.0,
        voting_period_blocks: int = 1008,  # ~1 week
        execution_delay_blocks: int = 144   # ~1 day
    ) -> str:
        """Create new governance proposal"""
        
        # Check proposer has minimum voting power
        proposer_power = self.vault_token.get_voting_power(proposer)
        min_proposal_power = 5.0  # 5% minimum to propose
        
        if proposer_power < min_proposal_power:
            raise ValueError(f"Proposer needs {min_proposal_power}% voting power, has {proposer_power}%")
        
        # Generate proposal ID
        self._proposal_counter += 1
        proposal_id = hashlib.sha256(
            f"{self.vault.vault_id}_{self._proposal_counter}_{proposer}".encode()
        ).hexdigest()[:16]
        
        # Create proposal
        proposal = GovernanceProposal(
            proposal_id=proposal_id,
            proposer=proposer,
            proposal_type=proposal_type,
            title=title,
            description=description,
            required_voting_power=required_voting_power,
            voting_period_blocks=voting_period_blocks,
            execution_delay_blocks=execution_delay_blocks,
            proposal_data=proposal_data,
            status=ProposalStatus.ACTIVE,
            votes_for=0,
            votes_against=0,
            voters=[],
            created_at_height=current_height,
            voting_ends_at_height=current_height + voting_period_blocks
        )
        
        self.proposals[proposal_id] = proposal
        return proposal_id
    
    def vote(self, proposal_id: str, voter: str, vote_for: bool, current_height: int) -> bool:
        """Vote on governance proposal"""
        
        if proposal_id not in self.proposals:
            return False
        
        proposal = self.proposals[proposal_id]
        
        # Check voting period
        if current_height > proposal.voting_ends_at_height:
            proposal.status = ProposalStatus.REJECTED
            return False
        
        # Check if already voted
        if voter in proposal.voters:
            return False
        
        # Get voting power
        voting_power = self.vault_token.balance_of(voter)
        if voting_power == 0:
            return False
        
        # Record vote
        proposal.voters.append(voter)
        
        if vote_for:
            proposal.votes_for += voting_power
        else:
            proposal.votes_against += voting_power
        
        return True
    
    def finalize_proposal(self, proposal_id: str, current_height: int) -> bool:
        """Finalize proposal after voting period"""
        
        if proposal_id not in self.proposals:
            return False
        
        proposal = self.proposals[proposal_id]
        
        # Check voting period ended
        if current_height <= proposal.voting_ends_at_height:
            return False
        
        # Calculate results
        total_votes = proposal.votes_for + proposal.votes_against
        if total_votes == 0:
            proposal.status = ProposalStatus.REJECTED
            return False
        
        votes_for_percentage = (proposal.votes_for / self.vault_token.total_supply) * 100
        
        if votes_for_percentage >= proposal.required_voting_power:
            proposal.status = ProposalStatus.PASSED
            proposal.execution_height = current_height + proposal.execution_delay_blocks
        else:
            proposal.status = ProposalStatus.REJECTED
        
        return True
    
    def execute_proposal(self, proposal_id: str, current_height: int) -> Dict[str, Any]:
        """Execute passed proposal"""
        
        if proposal_id not in self.proposals:
            raise ValueError("Proposal not found")
        
        proposal = self.proposals[proposal_id]
        
        if proposal.status != ProposalStatus.PASSED:
            raise ValueError("Proposal not passed")
        
        if proposal.execution_height is None or current_height < proposal.execution_height:
            raise ValueError("Execution delay not met")
        
        # Execute based on proposal type
        result = self._execute_proposal_action(proposal)
        
        proposal.status = ProposalStatus.EXECUTED
        return result
    
    def _execute_proposal_action(self, proposal: GovernanceProposal) -> Dict[str, Any]:
        """Execute specific proposal action"""
        
        if proposal.proposal_type == ProposalType.CHANGE_WITHDRAWAL_RULES:
            # Update withdrawal rules
            new_rules_data = proposal.proposal_data.get('new_rules', {})
            # In real implementation, would update vault rules
            return {'action': 'rules_updated', 'new_rules': new_rules_data}
        
        elif proposal.proposal_type == ProposalType.ADD_MEMBER:
            # Add new vault member
            new_member_data = proposal.proposal_data.get('new_member', {})
            # In real implementation, would add member to vault
            return {'action': 'member_added', 'member': new_member_data}
        
        elif proposal.proposal_type == ProposalType.REMOVE_MEMBER:
            # Remove vault member
            member_to_remove = proposal.proposal_data.get('member_pubkey', '')
            # In real implementation, would remove member from vault
            return {'action': 'member_removed', 'member': member_to_remove}
        
        elif proposal.proposal_type == ProposalType.EMERGENCY_EXIT:
            # Execute emergency exit
            # In real implementation, would trigger emergency withdrawal
            return {'action': 'emergency_exit_executed'}
        
        else:
            return {'action': 'unknown', 'proposal_type': proposal.proposal_type.value}
    
    def get_proposal(self, proposal_id: str) -> Optional[GovernanceProposal]:
        """Get proposal by ID"""
        return self.proposals.get(proposal_id)
    
    def get_active_proposals(self, current_height: int) -> List[GovernanceProposal]:
        """Get all active proposals"""
        active = []
        
        for proposal in self.proposals.values():
            if (proposal.status == ProposalStatus.ACTIVE and 
                current_height <= proposal.voting_ends_at_height):
                active.append(proposal)
        
        return active
    
    def get_proposal_results(self, proposal_id: str) -> Dict[str, Any]:
        """Get detailed proposal results"""
        
        if proposal_id not in self.proposals:
            return {}
        
        proposal = self.proposals[proposal_id]
        
        total_supply = self.vault_token.total_supply
        votes_for_pct = (proposal.votes_for / total_supply) * 100
        votes_against_pct = (proposal.votes_against / total_supply) * 100
        
        return {
            'proposal_id': proposal_id,
            'status': proposal.status.value,
            'votes_for': proposal.votes_for,
            'votes_against': proposal.votes_against,
            'votes_for_percentage': votes_for_pct,
            'votes_against_percentage': votes_against_pct,
            'required_percentage': proposal.required_voting_power,
            'total_voters': len(proposal.voters),
            'passed': votes_for_pct >= proposal.required_voting_power
        }
