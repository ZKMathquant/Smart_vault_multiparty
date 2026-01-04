import unittest
from src.vault import Vault, VaultMember, MultiPartyVault
from src.rules import WithdrawalRules
from src.predicate import WithdrawalRequest
from src.bitcoin_integration import BitcoinKey

class TestVault(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        # Generate test keys
        self.keys = []
        self.pubkeys = []
        for i in range(3):
            private_hex, public_hex = BitcoinKey.generate_key_pair()
            self.keys.append(private_hex)
            self.pubkeys.append(public_hex)

        # Create test vault members
        self.members = [
            VaultMember(self.pubkeys[0], 40, 100),
            VaultMember(self.pubkeys[1], 35, 100),
            VaultMember(self.pubkeys[2], 25, 100)
        ]

    def test_vault_creation(self):
        """Test vault creation and validation"""
        vault = Vault(self.members)
        self.assertEqual(len(vault.members), 3)
        self.assertEqual(vault.total_balance, 0)
        self.assertIsNotNone(vault.vault_id)

    def test_member_validation(self):
        """Test member share validation"""
        # Invalid shares (don't sum to 100)
        invalid_members = [
            VaultMember(self.pubkeys[0], 50, 100),
            VaultMember(self.pubkeys[1], 30, 100)  # Only 80% total
        ]
        
        with self.assertRaises(ValueError):
            Vault(invalid_members)

    def test_multiparty_vault(self):
        """Test MultiPartyVault functionality"""
        rules = WithdrawalRules.conservative()
        vault = MultiPartyVault(self.members, rules)
        vault.vault.total_balance = 100_000_000
        vault.vault.created_height = 100

        # Test member checking
        self.assertTrue(vault.vault.is_member(self.pubkeys[0]))
        self.assertFalse(vault.vault.is_member("invalid_key"))

        # Test share retrieval
        self.assertEqual(vault.vault.get_member_share(self.pubkeys[0]), 40)
        self.assertIsNone(vault.vault.get_member_share("invalid_key"))

if __name__ == '__main__':
    unittest.main()
