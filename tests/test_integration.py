import unittest
from src.vault import Vault, VaultMember, MultiPartyVault
from src.rules import WithdrawalRules
from src.predicate import WithdrawalRequest
from src.bos_stack.grail_pro import GrailProof
from src.bos_stack.zkbtc import ZkBtcBridge, ChainId, CrossChainVerifier
from src.bos_stack.charms import VaultToken, GovernanceSystem, ProposalType
from src.bitcoin_integration import BitcoinKey

class TestBOSIntegration(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        # Generate test keys
        self.keys = []
        self.pubkeys = []
        for i in range(3):
            private_hex, public_hex = BitcoinKey.generate_key_pair()
            self.keys.append(private_hex)
            self.pubkeys.append(public_hex)

        # Create test vault
        members = [
            VaultMember(self.pubkeys[0], 40, 100),
            VaultMember(self.pubkeys[1], 35, 100),
            VaultMember(self.pubkeys[2], 25, 100)
        ]

        rules = WithdrawalRules.conservative()
        self.vault = MultiPartyVault(members, rules)
        self.vault.vault.total_balance = 100_000_000
        self.vault.vault.created_height = 100

    def test_grail_pro_integration(self):
        """Test Grail Pro proof generation and verification"""
        request = WithdrawalRequest(
            amount=5_000_000,
            current_height=150,
            signers=[self.pubkeys[0], self.pubkeys[1]],
            is_emergency=False
        )

        # Generate proof
        proof = self.vault.create_withdrawal_proof(request)
        self.assertIsInstance(proof, GrailProof)

        # Check withdrawal amount
        self.assertEqual(proof.get_withdrawal_amount(), 5_000_000)
        
        # Verify predicate logic directly
        from src.predicate import VaultPredicate
        predicate = VaultPredicate(self.vault.vault, self.vault.rules, request)
        is_valid, reason = predicate.verify()
        self.assertTrue(is_valid)
        self.assertEqual(reason, "Withdrawal approved")

    def test_zkbtc_integration(self):
        """Test zkBTC cross-chain verification"""
        bridge = ZkBtcBridge.create_cross_chain_proof(
            self.vault.vault,
            ChainId.ETHEREUM
        )

        verifier = CrossChainVerifier()
        self.assertTrue(bridge.verify_on_chain(verifier))

        collateral = bridge.create_collateral_position(50_000_000)
        self.assertEqual(collateral['collateral_amount'], 50_000_000)
        self.assertIn('position_id', collateral)

    def test_charms_integration(self):
        """Test Charms token and governance integration"""
        token = VaultToken.create_for_vault(self.vault.vault)

        alice_balance = token.balance_of(self.pubkeys[0])
        self.assertEqual(alice_balance, 40_000_000)

        success = token.transfer(self.pubkeys[0], self.pubkeys[1], 5_000_000)
        self.assertTrue(success)

        self.assertEqual(token.balance_of(self.pubkeys[0]), 35_000_000)
        self.assertEqual(token.balance_of(self.pubkeys[1]), 40_000_000)

    def test_governance_system(self):
        """Test governance proposal and voting"""
        token = VaultToken.create_for_vault(self.vault.vault)
        governance = GovernanceSystem(token, self.vault.vault)

        proposal_id = governance.create_proposal(
            proposer=self.pubkeys[0],
            proposal_type=ProposalType.CHANGE_WITHDRAWAL_RULES,
            title="Reduce penalty rate",
            description="Reduce early withdrawal penalty from 10% to 5%",
            proposal_data={'new_penalty_rate': 500},
            current_height=200
        )

        self.assertTrue(governance.vote(proposal_id, self.pubkeys[0], True, 250))
        self.assertTrue(governance.vote(proposal_id, self.pubkeys[1], True, 250))

        self.assertTrue(governance.finalize_proposal(proposal_id, 1300))

        results = governance.get_proposal_results(proposal_id)
        self.assertTrue(results['passed'])
        self.assertGreaterEqual(results['votes_for_percentage'], 51.0)

if __name__ == '__main__':
    unittest.main()
