// Global variables
let currentVault = null;
let currentGovernance = null;
let createdVaults = {}; // Store created vaults persistently

// Tab management
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName + '-tab').classList.add('active');
    event.target.classList.add('active');
}

// Member management
function addMember() {
    const container = document.getElementById('members-container');
    const memberDiv = document.createElement('div');
    memberDiv.className = 'member-input';
    memberDiv.innerHTML = `
        <input type="text" placeholder="Member name" class="member-name">
        <input type="number" placeholder="Share %" class="member-share" min="1" max="100">
        <button onclick="removeMember(this)" style="background: #dc3545;">Remove</button>
    `;
    container.appendChild(memberDiv);
}

function removeMember(button) {
    button.parentElement.remove();
}

// Copy to clipboard function
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('Copied to clipboard!');
    }).catch(() => {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        alert('Copied to clipboard!');
    });
}

// Vault creation
async function createVault() {
    const memberInputs = document.querySelectorAll('.member-input');
    const members = [];
    let totalShares = 0;
    
    // Collect member data
    memberInputs.forEach(input => {
        const name = input.querySelector('.member-name').value.trim();
        const share = parseInt(input.querySelector('.member-share').value);
        
        if (name && share > 0) {
            members.push({ name, share });
            totalShares += share;
        }
    });
    
    // Validate
    if (members.length < 2) {
        showResult('create-result', 'Need at least 2 members', 'error');
        return;
    }
    
    if (totalShares !== 100) {
        showResult('create-result', `Shares must sum to 100%, got ${totalShares}%`, 'error');
        return;
    }
    
    const initialBalance = parseInt(document.getElementById('initial-balance').value);
    const rulesType = document.getElementById('rules-type').value;
    
    // Create vault
    try {
        const response = await fetch('/api/create_vault', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                members,
                initial_balance: initialBalance,
                rules_type: rulesType
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentVault = result;
            
            // Store vault data persistently
            createdVaults[result.vault_id] = result;
            
            let resultHtml = `
                <h3>✅ Vault Created Successfully!</h3>
                <p><strong>Vault ID:</strong> <code>${result.vault_id}</code></p>
                <p><strong>Balance:</strong> ${result.balance.toLocaleString()} sats</p>
                <p><strong>Commitment Hash:</strong> <code>${result.commitment_hash}</code></p>
                
                <h4>Members & Keys:</h4>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 10px 0;">
                    <p><strong>⚠️ Save these keys securely!</strong></p>
            `;
            
            result.members.forEach(member => {
                resultHtml += `
                    <div style="margin: 10px 0; padding: 10px; border: 1px solid #dee2e6; border-radius: 4px;">
                        <strong>${member.name} (${member.share}%)</strong><br>
                        <small>Public Key:</small> <code style="font-size: 11px;">${member.public_key}</code>
                        <button onclick="copyToClipboard('${member.public_key}')" style="margin-left: 10px; padding: 2px 6px;">Copy</button><br>
                        <small>Private Key:</small> <code style="font-size: 11px; color: #dc3545;">${member.private_key}</code>
                        <button onclick="copyToClipboard('${member.private_key}')" style="margin-left: 10px; padding: 2px 6px;">Copy</button>
                    </div>
                `;
            });
            
            // Add "Copy All Public Keys" button for multi-sig withdrawals
            const allPublicKeys = result.members.map(m => m.public_key).join('\n');
            resultHtml += `
                <div style="margin-top: 15px; text-align: center;">
                    <button onclick="copyToClipboard('${allPublicKeys}')" style="background: #28a745; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer;">
                        📋 Copy All Public Keys (for withdrawals)
                    </button>
                </div>
            `;
            
            resultHtml += `</div>`;
            
            showResult('create-result', resultHtml, 'success');
            
            // Auto-fill vault ID in manage tab
            document.getElementById('vault-id').value = result.vault_id;
            
        } else {
            showResult('create-result', result.error, 'error');
        }
        
    } catch (error) {
        showResult('create-result', 'Network error: ' + error.message, 'error');
    }
}

// Vault management
async function loadVault() {
    const vaultId = document.getElementById('vault-id').value.trim();
    
    if (!vaultId) {
        showResult('withdrawal-result', 'Please enter a vault ID', 'error');
        return;
    }
    
    // Check if we have this vault stored locally first
    if (createdVaults[vaultId]) {
        const storedVault = createdVaults[vaultId];
        
        // Build display with stored member info
        let membersHtml = '<h4>Member Public Keys (for withdrawals):</h4>';
        storedVault.members.forEach((member, index) => {
            membersHtml += `
                <div style="margin: 5px 0; padding: 8px; background: #f8f9fa; border-radius: 4px;">
                    <strong>${member.name} (${member.share}%):</strong><br>
                    <code style="font-size: 11px; word-break: break-all;">${member.public_key}</code>
                    <button onclick="copyToClipboard('${member.public_key}')" style="margin-left: 10px; padding: 2px 6px;">Copy</button>
                </div>
            `;
        });
        
        // Add copy all button for multi-sig
        const allKeys = storedVault.members.map(m => m.public_key).join('\n');
        membersHtml += `
            <div style="margin-top: 10px;">
                <button onclick="copyToClipboard('${allKeys}')" style="background: #28a745; color: white; padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer;">
                    📋 Copy All Public Keys
                </button>
            </div>
        `;
        
        const detailsHtml = `
            <p><strong>Vault ID:</strong> <code>${storedVault.vault_id}</code></p>
            <p><strong>Balance:</strong> ${storedVault.balance.toLocaleString()} sats</p>
            <p><strong>Members:</strong> ${storedVault.members.length}</p>
            <p><strong>Commitment Hash:</strong> <code>${storedVault.commitment_hash}</code></p>
            
            ${membersHtml}
            
            <h4>Withdrawal History:</h4>
            <p>No withdrawals yet (using stored vault data)</p>
        `;
        
        document.getElementById('vault-details').innerHTML = detailsHtml;
        document.getElementById('vault-info').style.display = 'block';
        currentVault = { vault_id: vaultId, balance: storedVault.balance };
        return;
    }
    
    // If not stored locally, fetch from server
    try {
        const response = await fetch(`/api/vault/${vaultId}`);
        const result = await response.json();
        
        if (response.ok) {
            currentVault = result;
            
            // Build member keys display
            let membersHtml = '';
            if (result.members && Array.isArray(result.members)) {
                membersHtml = '<h4>Member Public Keys (for withdrawals):</h4>';
                result.members.forEach((member, index) => {
                    membersHtml += `
                        <div style="margin: 5px 0; padding: 8px; background: #f8f9fa; border-radius: 4px;">
                            <strong>Member ${index + 1} (${member.share}%):</strong><br>
                            <code style="font-size: 11px; word-break: break-all;">${member.pubkey}</code>
                            <button onclick="copyToClipboard('${member.pubkey}')" style="margin-left: 10px; padding: 2px 6px;">Copy</button>
                        </div>
                    `;
                });
                
                // Add copy all button
                const allKeys = result.members.map(m => m.pubkey).join('\n');
                membersHtml += `
                    <div style="margin-top: 10px;">
                        <button onclick="copyToClipboard('${allKeys}')" style="background: #28a745; color: white; padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer;">
                            📋 Copy All Public Keys
                        </button>
                    </div>
                `;
            }
            
            const detailsHtml = `
                <p><strong>Vault ID:</strong> <code>${result.vault_id}</code></p>
                <p><strong>Balance:</strong> ${result.balance.toLocaleString()} sats</p>
                <p><strong>Members:</strong> ${Array.isArray(result.members) ? result.members.length : result.members}</p>
                <p><strong>Commitment Hash:</strong> <code>${result.commitment_hash}</code></p>
                ${result.token ? `<p><strong>Token:</strong> ${result.token.symbol} (${result.token.total_supply.toLocaleString()} supply)</p>` : ''}
                
                ${membersHtml}
                
                <h4>Withdrawal History:</h4>
                ${result.withdrawal_history.length > 0 ? 
                    result.withdrawal_history.map(w => 
                        `<div>Block ${w.height}: ${w.amount.toLocaleString()} sats (${w.signers.length} signers)</div>`
                    ).join('') : 
                    '<p>No withdrawals yet</p>'
                }
            `;
            
            document.getElementById('vault-details').innerHTML = detailsHtml;
            document.getElementById('vault-info').style.display = 'block';
            
        } else {
            showResult('withdrawal-result', result.error, 'error');
        }
        
    } catch (error) {
        showResult('withdrawal-result', 'Network error: ' + error.message, 'error');
    }
}

async function createWithdrawal() {
    if (!currentVault) {
        showResult('withdrawal-result', 'Please load a vault first', 'error');
        return;
    }
    
    const amount = parseInt(document.getElementById('withdrawal-amount').value);
    const signersText = document.getElementById('withdrawal-signers').value.trim();
    const isEmergency = document.getElementById('is-emergency').checked;
    
    if (!amount || amount <= 0) {
        showResult('withdrawal-result', 'Please enter a valid amount', 'error');
        return;
    }
    
    if (!signersText) {
        showResult('withdrawal-result', 'Please enter signer public keys', 'error');
        return;
    }
    
    const signers = signersText.split('\n').map(s => s.trim()).filter(s => s.length > 0);
    
    try {
        const response = await fetch(`/api/vault/${currentVault.vault_id}/withdraw`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                amount,
                signers,
                is_emergency: isEmergency,
                current_height: 150
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            const resultHtml = `
                <h3>✅ Withdrawal Successful!</h3>
                <p><strong>Withdrawal Amount:</strong> ${result.withdrawal_amount.toLocaleString()} sats</p>
                <p><strong>Penalty:</strong> ${result.penalty.toLocaleString()} sats</p>
                <p><strong>Remaining Balance:</strong> ${result.remaining_balance.toLocaleString()} sats</p>
                <p><strong>Transaction ID:</strong> <code>${result.transaction_id}</code></p>
            `;
            showResult('withdrawal-result', resultHtml, 'success');
            
            // Update stored vault balance if it exists
            const vaultId = currentVault.vault_id;
            if (createdVaults[vaultId]) {
                createdVaults[vaultId].balance = result.remaining_balance;
            }
            
            // Reload vault info
            loadVault();
            
        } else {
            showResult('withdrawal-result', result.error, 'error');
        }
        
    } catch (error) {
        showResult('withdrawal-result', 'Network error: ' + error.message, 'error');
    }
}

// Governance
async function loadGovernance() {
    const vaultId = document.getElementById('gov-vault-id').value.trim();
    
    if (!vaultId) {
        showResult('governance-result', 'Please enter a vault ID', 'error');
        return;
    }
    
    try {
        // Load vault info
        const vaultResponse = await fetch(`/api/vault/${vaultId}`);
        const vaultResult = await vaultResponse.json();
        
        if (vaultResponse.ok) {
            currentGovernance = { vault_id: vaultId, vault: vaultResult };
            document.getElementById('governance-info').style.display = 'block';
            
            // Load proposals
            loadProposals();
            
        } else {
            showResult('governance-result', vaultResult.error, 'error');
        }
        
    } catch (error) {
        showResult('governance-result', 'Network error: ' + error.message, 'error');
    }
}

async function createProposal() {
    if (!currentGovernance) {
        showResult('governance-result', 'Please load governance first', 'error');
        return;
    }
    
    const proposer = document.getElementById('proposer-key').value.trim();
    const proposalType = document.getElementById('proposal-type').value;
    const title = document.getElementById('proposal-title').value.trim();
    const description = document.getElementById('proposal-description').value.trim();
    
    if (!proposer || !title || !description) {
        showResult('governance-result', 'Please fill all fields', 'error');
        return;
    }
    
    try {
        const response = await fetch(`/api/vault/${currentGovernance.vault_id}/governance/propose`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                proposer,
                proposal_type: proposalType,
                title,
                description,
                proposal_data: {},
                current_height: 200
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showResult('governance-result', `✅ Proposal created: ${result.proposal_id}`, 'success');
            
            // Clear form
            document.getElementById('proposal-title').value = '';
            document.getElementById('proposal-description').value = '';
            
            // Reload proposals
            loadProposals();
            
        } else {
            showResult('governance-result', result.error, 'error');
        }
        
    } catch (error) {
        showResult('governance-result', 'Network error: ' + error.message, 'error');
    }
}

async function loadProposals() {
    if (!currentGovernance) return;
    
    try {
        const response = await fetch(`/api/vault/${currentGovernance.vault_id}/governance/proposals?current_height=300`);
        const result = await response.json();
        
        if (response.ok) {
            const proposalsList = document.getElementById('proposals-list');
            
            if (result.proposals.length === 0) {
                proposalsList.innerHTML = '<p>No active proposals</p>';
                return;
            }
            
            let proposalsHtml = '';
            result.proposals.forEach(proposal => {
                proposalsHtml += `
                    <div class="proposal-item">
                        <h4>${proposal.title}</h4>
                        <p>${proposal.description}</p>
                        <p><strong>Type:</strong> ${proposal.proposal_type.replace('_', ' ')}</p>
                        <p><strong>Status:</strong> <span class="status ${proposal.status}">${proposal.status}</span></p>
                        <p><strong>Votes FOR:</strong> ${proposal.votes_for_percentage.toFixed(1)}%</p>
                        <p><strong>Votes AGAINST:</strong> ${proposal.votes_against_percentage.toFixed(1)}%</p>
                        <p><strong>Required:</strong> ${proposal.required_percentage}%</p>
                        
                        <div style="margin-top: 10px;">
                            <input type="text" placeholder="Voter public key" id="voter-${proposal.proposal_id}" style="width: 300px; margin-right: 10px;">
                            <button onclick="voteProposal('${proposal.proposal_id}', true)">Vote YES</button>
                            <button onclick="voteProposal('${proposal.proposal_id}', false)">Vote NO</button>
                        </div>
                    </div>
                `;
            });
            
            proposalsList.innerHTML = proposalsHtml;
            
        } else {
            console.error('Failed to load proposals:', result.error);
        }
        
    } catch (error) {
        console.error('Network error loading proposals:', error);
    }
}

async function voteProposal(proposalId, voteFor) {
    const voterKey = document.getElementById(`voter-${proposalId}`).value.trim();
    
    if (!voterKey) {
        showResult('governance-result', 'Please enter voter public key', 'error');
        return;
    }
    
    try {
        const response = await fetch(`/api/vault/${currentGovernance.vault_id}/governance/vote`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                proposal_id: proposalId,
                voter: voterKey,
                vote_for: voteFor,
                current_height: 250
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showResult('governance-result', `✅ Vote recorded: ${voteFor ? 'YES' : 'NO'}`, 'success');
            
            // Reload proposals to show updated results
            setTimeout(loadProposals, 1000);
            
        } else {
            showResult('governance-result', result.error, 'error');
        }
        
    } catch (error) {
        showResult('governance-result', 'Network error: ' + error.message, 'error');
    }
}

// Utility functions
function showResult(elementId, message, type) {
    const element = document.getElementById(elementId);
    element.innerHTML = message;
    element.className = `result ${type}`;
    element.style.display = 'block';
    
    // Only auto-hide withdrawal and governance results, NOT vault creation
    if (type === 'success' && elementId !== 'create-result') {
        setTimeout(() => {
            element.style.display = 'none';
        }, 10000);
    }
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    // Set default values
    document.getElementById('initial-balance').value = 100000000;
    
    // Add event listeners for Enter key
    document.getElementById('vault-id').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            loadVault();
        }
    });
    
    document.getElementById('gov-vault-id').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            loadGovernance();
        }
    });
});
