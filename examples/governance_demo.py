#!/usr/bin/env python3
"""
Example: Governance and token management demo
"""

from src.vault import VaultMember, MultiPartyVault
from src.rules import WithdrawalRules
from src.bitcoin_integration import BitcoinKey
from src.bos_stack.charms import VaultToken, GovernanceSystem, ProposalType

def main():
    print("=== Governance and Token Demo ===")
    print()
    
    # Setup vault
    print("🏗️  Setting up governance vault...")
    
    # Generate keys
    keys_data = []
    for name in ["Alice", "Bob", "Carol"]:
        private_hex, public_hex = BitcoinKey.generate_key_pair()
        keys_data.append({'name': name, 'private': private_hex, 'public': public_hex})
    
    # Create vault
    members = [
        VaultMember(keys_data[0]['public'], 40, 100),  # Alice 40%
        VaultMember(keys_data[1]['public'], 35, 100),  # Bob 35%
        VaultMember(keys_data[2]['public'], 25, 100),  # Carol 25%
    ]
    
    rules = WithdrawalRules.conservative()
    vault = MultiPartyVault(members, rules)
    vault.vault.total_balance = 100_000_000
    vault.vault.created_height = 100
    
    # Create governance system
    token = VaultToken.create_for_vault(vault.vault)
    governance = GovernanceSystem(token, vault.vault)
    
    print(f"   Token: {token.metadata.symbol}")
    print(f"   Total Supply: {token.total_supply:,}")
    print()
    
    # Show initial token distribution
    print("💰 Initial Token Distribution:")
    for i, data in enumerate(keys_data):
        balance = token.balance_of(data['public'])
        voting_power = token.get_voting_power(data['public'])
        print(f"   {data['name']}: {balance:,} tokens ({voting_power:.1f}% voting power)")
    print()
    
    # Test token transfer
    print("🔄 Testing Token Transfer...")
    print("   Alice transfers 5M tokens to Bob")
    
    alice_key = keys_data[0]['public']
    bob_key = keys_data[1]['public']
    
    success = token.transfer(alice_key, bob_key, 5_000_000)
    if success:
        print("   ✅ Transfer successful")
        print(f"   Alice new balance: {token.balance_of(alice_key):,}")
        print(f"   Bob new balance: {token.balance_of(bob_key):,}")
    else:
        print("   ❌ Transfer failed")
    print()
    
    # Create governance proposal
    print("🗳️  Creating Governance Proposal...")
    
    proposal_id = governance.create_proposal(
        proposer=alice_key,
        proposal_type=ProposalType.CHANGE_WITHDRAWAL_RULES,
        title="Reduce Early Withdrawal Penalty",
        description="Reduce penalty from 10% to 5% to make vault more flexible",
        proposal_data={
            'new_penalty_rate': 500,  # 5%
            'reason': 'Market conditions favor lower penalties'
        },
        current_height=200,
        required_voting_power=51.0,
        voting_period_blocks=1008
    )
    
    print(f"   Proposal ID: {proposal_id}")
    print(f"   Proposer: Alice")
    print(f"   Type: Change Withdrawal Rules")
    print(f"   Required voting power: 51%")
    print()
    
    # Voting phase
    print("🗳️  Voting Phase...")
    
    # Alice votes YES (35% after transfer)
    alice_vote = governance.vote(proposal_id, alice_key, True, 250)
    alice_power = token.get_voting_power(alice_key)
    print(f"   Alice votes YES ({alice_power:.1f}% power): {'✅' if alice_vote else '❌'}")
    
    # Bob votes YES (40% after receiving transfer)
    bob_vote = governance.vote(proposal_id, bob_key, True, 300)
    bob_power = token.get_voting_power(bob_key)
    print(f"   Bob votes YES ({bob_power:.1f}% power): {'✅' if bob_vote else '❌'}")
    
    # Carol votes NO (25%)
    carol_key = keys_data[2]['public']
    carol_vote = governance.vote(proposal_id, carol_key, False, 350)
    carol_power = token.get_voting_power(carol_key)
    print(f"   Carol votes NO ({carol_power:.1f}% power): {'✅' if carol_vote else '❌'}")
    
    print()
    
    # Finalize proposal
    print("📊 Finalizing Proposal...")
    
    # End voting period
    finalized = governance.finalize_proposal(proposal_id, 1300)  # After voting period
    
    if finalized:
        results = governance.get_proposal_results(proposal_id)
        print(f"   Votes FOR: {results['votes_for_percentage']:.1f}%")
        print(f"   Votes AGAINST: {results['votes_against_percentage']:.1f}%")
        print(f"   Required: {results['required_percentage']}%")
        print(f"   Status: {'✅ PASSED' if results['passed'] else '❌ REJECTED'}")
        
        if results['passed']:
            print()
            print("⚡ Executing Proposal...")
            
            # Execute proposal
            execution_result = governance.execute_proposal(proposal_id, 1450)  # After delay
            print(f"   Execution result: {execution_result}")
            print("   ✅ Withdrawal rules updated!")
        
    else:
        print("   ❌ Proposal finalization failed")
    
    print()
    
    # Show final state
    print("📈 Final Governance State:")
    active_proposals = governance.get_active_proposals(1500)
    print(f"   Active proposals: {len(active_proposals)}")
    
    transfer_history = token.get_transfer_history()
    print(f"   Token transfers: {len(transfer_history)}")
    
    print()
    print("✅ Governance demo complete!")
    print("   - Tokens distributed and transferred")
    print("   - Proposal created and voted on")
    print("   - Democratic governance in action")

if __name__ == "__main__":
    main()
