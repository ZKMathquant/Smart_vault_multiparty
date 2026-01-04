import unittest
from src.rules import WithdrawalRules

class TestWithdrawalRules(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.conservative_rules = WithdrawalRules.conservative()
        self.permissive_rules = WithdrawalRules.permissive()

    def test_conservative_rules(self):
        """Test conservative rule parameters"""
        rules = self.conservative_rules

        self.assertEqual(rules.min_signers, 2)
        self.assertEqual(rules.large_withdrawal_threshold, 10_000_000)
        self.assertTrue(rules.large_withdrawal_requires_all)
        self.assertEqual(rules.early_withdrawal_penalty_bps, 1000)  # 10%

    def test_permissive_rules(self):
        """Test permissive rule parameters"""
        rules = self.permissive_rules

        self.assertEqual(rules.min_signers, 1)
        self.assertEqual(rules.large_withdrawal_threshold, 50_000_000)
        self.assertFalse(rules.large_withdrawal_requires_all)
        self.assertEqual(rules.early_withdrawal_penalty_bps, 500)  # 5%

    def test_penalty_calculation(self):
        """Test penalty calculation"""
        rules = self.conservative_rules
        rules.penalty_free_height = 1000

        # Before penalty-free height
        penalty = rules.calculate_penalty(100_000_000, 500)  # 1 BTC at height 500
        self.assertEqual(penalty, 10_000_000)  # 10% penalty = 0.1 BTC

        # After penalty-free height
        no_penalty = rules.calculate_penalty(100_000_000, 1001)
        self.assertEqual(no_penalty, 0)

    def test_large_withdrawal_detection(self):
        """Test large withdrawal detection"""
        rules = self.conservative_rules

        self.assertFalse(rules.is_large_withdrawal(5_000_000))   # 0.05 BTC
        self.assertTrue(rules.is_large_withdrawal(15_000_000))   # 0.15 BTC

    def test_withdrawal_validation(self):
        """Test withdrawal validation logic"""
        rules = self.conservative_rules

        # Small withdrawal with sufficient signers
        is_valid, reason = rules.validate_withdrawal(5_000_000, 2, 3)
        self.assertTrue(is_valid)

        # Small withdrawal with insufficient signers
        is_valid, reason = rules.validate_withdrawal(5_000_000, 1, 3)
        self.assertFalse(is_valid)
        self.assertIn("Need at least 2 signers", reason)

        # Large withdrawal with sufficient signers
        is_valid, reason = rules.validate_withdrawal(50_000_000, 3, 3)
        self.assertTrue(is_valid)

if __name__ == '__main__':
    unittest.main()
