#!/usr/bin/env python3
"""
Web interface for Multi-Party Smart Vault
"""

from flask import Flask, render_template, request, jsonify, session
import json
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.vault import VaultMember, MultiPartyVault
from src.rules import WithdrawalRules
from src.predicate import WithdrawalRequest
from src.bitcoin_integration import BitcoinKey
from src.bos_stack.charms import VaultToken, GovernanceSystem, ProposalType

app = Flask(__name__)
app.secret_key = 'demo_secret_key_change_in_production'

# Global storage (in production, use proper database)
vaults = {}
governance_systems = {}
vault_keys = {}  # Store member keys separately

@app.route('/')
def index():
    """Main vault interface"""
    return render_template('index.html')

@app.route('/api/create_vault', methods=['POST'])
def create_vault():
    """Create new multi-party vault"""
    try:
        data = request.json
        
        # Generate keys for members
        members = []
        keys_info = []
        
        for member_data in data['members']:
            private_hex, public_hex = BitcoinKey.generate_key_pair()
            
            member = VaultMember(
                pubkey=public_hex,
                share_percentage=member_data['share'],
                join_height=100
            )
            members.append(member)
            
            keys_info.append({
                'name': member_data['name'],
                'public_key': public_hex,
                'private_key': private_hex,
                'share': member_data['share']
            })
        
        # Create rules
        if data.get('rules_type') == 'permissive':
            rules = WithdrawalRules.permissive()
        else:
            rules = WithdrawalRules.conservative()
        
        # Create vault
        vault = MultiPartyVault(members, rules)
        vault.vault.total_balance = data.get('initial_balance', 100_000_000)
        vault.vault.created_height = 100
        
        # Store vault and keys
        vault_id = vault.vault.vault_id
        vaults[vault_id] = vault
        vault_keys[vault_id] = keys_info  # Store keys separately
        
        # Create governance token
        token = VaultToken.create_for_vault(vault.vault)
        governance = GovernanceSystem(token, vault.vault)
        governance_systems[vault_id] = {'token': token, 'governance': governance}
        
        print(f"DEBUG: Created vault {vault_id} with members: {[m.pubkey for m in members]}")
        
        return jsonify({
            'success': True,
            'vault_id': vault_id,
            'commitment_hash': vault.vault.commitment_hash(),
            'balance': vault.vault.total_balance,
            'members': keys_info,
            'rules': {
                'min_signers': rules.min_signers,
                'large_threshold': rules.large_withdrawal_threshold,
                'penalty_rate': rules.early_withdrawal_penalty_bps / 100
            }
        })
        
    except Exception as e:
        print(f"ERROR creating vault: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/vault/<vault_id>')
def get_vault(vault_id):
    """Get vault information"""
    if vault_id not in vaults:
        return jsonify({'error': 'Vault not found'}), 404
    
    vault = vaults[vault_id]
    gov_data = governance_systems.get(vault_id)
    keys_data = vault_keys.get(vault_id, [])
    
    # Include member public keys for reference
    members_info = []
    for i, member in enumerate(vault.vault.members):
        member_info = {
            'pubkey': member.pubkey,
            'share': member.share_percentage
        }
        # Add name if available from stored keys
        if i < len(keys_data):
            member_info['name'] = keys_data[i]['name']
        members_info.append(member_info)
    
    vault_info = {
        'vault_id': vault_id,
        'balance': vault.vault.total_balance,
        'members': members_info,  # Now includes pubkeys and names
        'commitment_hash': vault.vault.commitment_hash(),
        'withdrawal_history': vault.get_withdrawal_history()
    }
    
    if gov_data:
        token = gov_data['token']
        vault_info['token'] = {
            'name': token.metadata.name,
            'symbol': token.metadata.symbol,
            'total_supply': token.total_supply
        }
    
    print(f"DEBUG: Returning vault info for {vault_id}: {len(members_info)} members")
    return jsonify(vault_info)

@app.route('/api/vault/<vault_id>/withdraw', methods=['POST'])
def create_withdrawal(vault_id):
    """Create withdrawal from vault"""
    if vault_id not in vaults:
        return jsonify({'error': 'Vault not found'}), 404
    
    try:
        data = request.json
        vault = vaults[vault_id]
        
        print(f"DEBUG: Withdrawal request for vault {vault_id}")
        print(f"DEBUG: Amount: {data['amount']}")
        print(f"DEBUG: Signers: {data['signers']}")
        print(f"DEBUG: Vault members: {[m.pubkey for m in vault.vault.members]}")
        
        # Create withdrawal request
        request_obj = WithdrawalRequest(
            amount=data['amount'],
            current_height=data.get('current_height', 150),
            signers=data['signers'],
            is_emergency=data.get('is_emergency', False),
            recipient_address=data.get('recipient_address')
        )
        
        # Generate proof
        proof = vault.create_withdrawal_proof(request_obj)
        
        # Execute withdrawal
        result = vault.execute_withdrawal(proof)
        
        return jsonify({
            'success': True,
            'withdrawal_amount': result['withdrawal_amount'],
            'remaining_balance': result['remaining_balance'],
            'transaction_id': result['transaction_id'],
            'penalty': proof.get_penalty_amount()
        })
        
    except Exception as e:
        print(f"ERROR in withdrawal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/vault/<vault_id>/governance/propose', methods=['POST'])
def create_proposal(vault_id):
    """Create governance proposal"""
    if vault_id not in vaults or vault_id not in governance_systems:
        return jsonify({'error': 'Vault or governance not found'}), 404
    
    try:
        data = request.json
        governance = governance_systems[vault_id]['governance']
        
        proposal_id = governance.create_proposal(
            proposer=data['proposer'],
            proposal_type=ProposalType(data['proposal_type']),
            title=data['title'],
            description=data['description'],
            proposal_data=data.get('proposal_data', {}),
            current_height=data.get('current_height', 200)
        )
        
        return jsonify({
            'success': True,
            'proposal_id': proposal_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/vault/<vault_id>/governance/vote', methods=['POST'])
def vote_proposal(vault_id):
    """Vote on governance proposal"""
    if vault_id not in governance_systems:
        return jsonify({'error': 'Governance not found'}), 404
    
    try:
        data = request.json
        governance = governance_systems[vault_id]['governance']
        
        success = governance.vote(
            proposal_id=data['proposal_id'],
            voter=data['voter'],
            vote_for=data['vote_for'],
            current_height=data.get('current_height', 250)
        )
        
        return jsonify({'success': success})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/vault/<vault_id>/governance/proposals')
def get_proposals(vault_id):
    """Get governance proposals"""
    if vault_id not in governance_systems:
        return jsonify({'error': 'Governance not found'}), 404
    
    governance = governance_systems[vault_id]['governance']
    current_height = request.args.get('current_height', 300, type=int)
    
    active_proposals = governance.get_active_proposals(current_height)
    
    proposals_data = []
    for proposal in active_proposals:
        results = governance.get_proposal_results(proposal.proposal_id)
        proposals_data.append({
            'proposal_id': proposal.proposal_id,
            'title': proposal.title,
            'description': proposal.description,
            'proposal_type': proposal.proposal_type.value,
            'status': proposal.status.value,
            'votes_for_percentage': results.get('votes_for_percentage', 0),
            'votes_against_percentage': results.get('votes_against_percentage', 0),
            'required_percentage': proposal.required_voting_power
        })
    
    return jsonify({'proposals': proposals_data})

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )

