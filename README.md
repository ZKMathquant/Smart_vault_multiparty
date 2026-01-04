# Multi-Party Smart Vault

Bitcoin joint accounts with programmable withdrawal rules using **BitcoinOS-aligned interfaces**.

## BOS Stack Integration (Python Implementation)

- **Charms**: Programmable token standard for vault shares and governance
- **Grail Pro**: Zero-knowledge proof system for UTXO-based vault verification  
- **zkBTC**: Cross-chain proof verification for multi-chain vault operations

**Implementation**: Pure Python with BOS-aligned interfaces. Cryptographic operations use standard libraries with BOS-compatible APIs.

## What This Enables

**Multi-party Bitcoin custody with:**
- Dynamic quorum rules (2-of-3, but large withdrawals need unanimity)
- Amount-dependent withdrawal policies
- Time-based penalty mechanisms
- Cross-chain vault state verification
- Programmable vault share tokens

## Core Innovation

Bitcoin enforces **cryptographic proofs of rule compliance**, not the rules themselves.

## Quick Start

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run complete demo
python3 demo.py

# Start web interface
python3 web_interface/app.py



# Run tests
python3 -m unittest discover tests/ -v

# Run individual examples
python3 examples/create_vault.py
python3 examples/test_withdrawals.py
python3 examples/governance_demo.py







Architecture
Vault State: Python classes with Bitcoin-compatible serialization

Withdrawal Rules: Programmable policy engine

zk Proofs: Grail Pro-compatible proof generation

Cross-chain: zkBTC-style verification interfaces

Governance: Charms-compatible token system

Why This Matters
Enables programmable Bitcoin custody that Bitcoin Script cannot express while remaining fully implementable and testable.
