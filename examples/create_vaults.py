#!/usr/bin/env python3
"""
Example: Creating a multi-party smart vault
"""

from src.vault import VaultMember, MultiPartyVault
from src.rules import WithdrawalRules
from src.bitcoin_integration import BitcoinKey
from src.bos_stack.charms import VaultToken

def main():
    print("=== Creating Multi-Party Smart Vault ===")
    print()
    
    # Generate keys for 3 members
    print("🔑 Generating Bitcoin keys for vault members...")
    members_data = []
    
    for i, (name, share) in enumerate([("Alice", 40), ("Bob", 35), ("Carol", 25)]):
        private_hex, public_hex = BitcoinKey.generate_key_pair()
        members_data.append({
            'name': name,
            'private_key': private_hex,
            'public_key': public_hex,
            'share': share
        })
        print(f"   {name}: {public_hex[:16]}... ({share}%)")
    
    print()
    
    # Create vault members
    members = []
    for data in members_data:
        member = VaultMember(
            pubkey=data['public_key'],
            share_percentage=data['share'],
            join_height=100
        )
        members.append(member)
    
    # Create withdrawal rules
    rules = WithdrawalRules.conservative()
    print("📋 Vault Rules:")
    print(f"   Min signers: {rules.min_signers}")
    print(f"   Large withdrawal threshold: {rules.large_withdrawal_threshold:,} sats")
    print(f"   Large withdrawals require all: {rules.large_withdrawal_requires_all}")
    print(f"   Early withdrawal penalty: {rules.early_withdrawal_penalty_bps/100}%")
    print()
    
    # Create vault
    vault = MultiPartyVault(members, rules)
    vault.vault.total_balance = 100_000_000  # 1 BTC
    vault.vault.created_height = 100
    
    print("🏗️  Vault Created Successfully!")
    print(f"   Vault ID: {vault.vault.vault_id}")
    print(f"   Balance: {vault.vault.total_balance:,} sats (1.0 BTC)")
    print(f"   Members: {len(vault.vault.members)}")
    print(f"   Commitment Hash: {vault.vault.commitment_hash()}")
    print()
    
    # Create Charms tokens
    print("🪙 Creating Charms governance tokens...")
    token = VaultToken.create_for_vault(vault.vault)
    
    print(f"   Token Name: {token.metadata.name}")
    print(f"   Token Symbol: {token.metadata.symbol}")
    print(f"   Total Supply: {token.total_supply:,}")
    print()
    
    print("💰 Token Distribution:")
    for i, data in enumerate(members_data):
        balance = token.balance_of(data['public_key'])
        print(f"   {data['name']}: {balance:,} {token.metadata.symbol} ({data['share']}%)")
    
    print()
    print("✅ Multi-party vault setup complete!")
    print("   - Bitcoin keys generated and secured")
    print("   - Vault rules configured")
    print("   - Governance tokens distributed")
    print("   - Ready for withdrawals and governance")

if __name__ == "__main__":
    main()
