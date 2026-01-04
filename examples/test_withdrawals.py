#!/usr/bin/env python3
"""
Example: Testing various withdrawal scenarios
"""

from src.vault import VaultMember, MultiPartyVault
from src.rules import WithdrawalRules
from src.predicate import WithdrawalRequest
from src.bitcoin_integration import BitcoinKey

def main():
    print("=== Testing Withdrawal Scenarios ===")
    print()
    
    # Setup vault
    print("🏗️  Setting up test vault...")
    
    # Generate keys
    keys_data = []
    for name in ["Alice", "Bob", "Carol"]:
        private_hex, public_hex = BitcoinKey.generate_key_pair()
        keys_data.append({'name': name, 'private': private_hex, 'public': public_hex})
    
    # Create members
    members = [
        VaultMember(keys_data[0]['public'], 40, 100),  # Alice 40%
        VaultMember(keys_data[1]['public'], 35, 100),  # Bob 35%
        VaultMember(keys_data[2]['public'], 25, 100),  # Carol 25%
    ]
    
    # Create vault
    rules = WithdrawalRules.conservative()
    vault = MultiPartyVault(members, rules)
    vault.vault.total_balance = 100_000_000  # 1 BTC
    vault.vault.created_height = 100
    
    print(f"   Vault Balance: {vault.vault.total_balance:,} sats")
    print(f"   Large withdrawal threshold: {rules.large_withdrawal_threshold:,} sats")
    print()
    
    # Test scenarios
    scenarios = [
        {
            'name': 'Small withdrawal (2-of-3)',
            'amount': 5_000_000,  # 0.05 BTC
            'signers': [keys_data[0]['public'], keys_data[1]['public']],  # Alice + Bob
            'should_pass': True
        },
        {
            'name': 'Large withdrawal (2-of-3) - Should fail',
            'amount': 50_000_000,  # 0.5 BTC
            'signers': [keys_data[0]['public'], keys_data[1]['public']],  # Alice + Bob
            'should_pass': False
        },
        {
            'name': 'Large withdrawal (3-of-3)',
            'amount': 50_000_000,  # 0.5 BTC
            'signers': [k['public'] for k in keys_data],  # All members
            'should_pass': True
        },
        {
            'name': 'Excessive withdrawal',
            'amount': 150_000_000,  # 1.5 BTC (more than max)
            'signers': [k['public'] for k in keys_data],
            'should_pass': False
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"📝 Test {i}: {scenario['name']}")
        print(f"   Amount: {scenario['amount']:,} sats ({scenario['amount']/100_000_000:.2f} BTC)")
        print(f"   Signers: {len(scenario['signers'])}")
        
        # Create withdrawal request
        request = WithdrawalRequest(
            amount=scenario['amount'],
            current_height=150,
            signers=scenario['signers'],
            is_emergency=False
        )
        
        try:
            # Generate proof
            proof = vault.create_withdrawal_proof(request)
            
            # Verify proof
            if vault.verify_withdrawal(proof):
                print(f"   ✅ Proof generated and verified")
                print(f"   💰 Net withdrawal: {proof.get_withdrawal_amount():,} sats")
                print(f"   💸 Penalty: {proof.get_penalty_amount():,} sats")
                
                if scenario['should_pass']:
                    print(f"   ✅ Expected result: PASS")
                else:
                    print(f"   ❌ Unexpected result: Should have failed")
            else:
                print(f"   ❌ Proof verification failed")
                
        except ValueError as e:
            print(f"   ❌ Withdrawal rejected: {e}")
            if not scenario['should_pass']:
                print(f"   ✅ Expected result: FAIL")
            else:
                print(f"   ❌ Unexpected result: Should have passed")
        
        print()
    
    # Test emergency withdrawal
    print("🚨 Testing Emergency Withdrawal")
    print("   Simulating vault created 1+ years ago...")
    
    # Make vault old enough for emergency
    vault.vault.created_height = 50
    
    emergency_request = WithdrawalRequest(
        amount=vault.vault.total_balance,  # Full balance
        current_height=52610,  # More than 1 year later
        signers=[keys_data[0]['public']],  # Single signer (Alice)
        is_emergency=True
    )
    
    try:
        proof = vault.create_withdrawal_proof(emergency_request)
        if vault.verify_withdrawal(proof):
            print("   ✅ Emergency withdrawal approved")
            print(f"   💰 Emergency amount: {proof.get_withdrawal_amount():,} sats")
        else:
            print("   ❌ Emergency withdrawal verification failed")
    except ValueError as e:
        print(f"   ❌ Emergency withdrawal rejected: {e}")
    
    print()
    print("🎯 Withdrawal testing complete!")

if __name__ == "__main__":
    main()
