"""
Unit and integration tests for Issue #19:
Make moratorium interest-capitalisation an explicit, user-visible choice.
"""
import unittest
from fastapi.testclient import TestClient

from deterministic import calc_emi, calc_repayment_schedule
from main import app


class TestRepaymentScheduleCalculations(unittest.TestCase):
    def setUp(self):
        self.principal = 100000.0
        self.annual_rate_pct = 6.0
        self.tenure_months = 60
        self.moratorium_months = 6

    def test_case_a_no_moratorium(self):
        """Case A — No moratorium:
        Capitalised and non-capitalised modes should produce the same result when moratorium_months = 0.
        """
        res_non_cap = calc_repayment_schedule(
            principal=self.principal,
            annual_rate_pct=self.annual_rate_pct,
            tenure_months=self.tenure_months,
            moratorium_months=0,
            capitalise_moratorium_interest=False,
        )
        res_cap = calc_repayment_schedule(
            principal=self.principal,
            annual_rate_pct=self.annual_rate_pct,
            tenure_months=self.tenure_months,
            moratorium_months=0,
            capitalise_moratorium_interest=True,
        )

        self.assertEqual(res_cap["moratorium_interest"], 0.0)
        self.assertEqual(res_cap["effective_principal"], self.principal)
        self.assertAlmostEqual(res_non_cap["monthly_emi"], res_cap["monthly_emi"], places=4)
        self.assertAlmostEqual(res_non_cap["total_repayment"], res_cap["total_repayment"], places=4)
        self.assertAlmostEqual(res_cap["emi_difference"], 0.0, places=4)
        self.assertAlmostEqual(res_cap["total_repayment_difference"], 0.0, places=4)

    def test_case_b_nonzero_moratorium(self):
        """Case B — Non-zero moratorium:
        Capitalised mode should produce capitalised_principal > original_principal
        when the interest rate and moratorium are non-zero.
        Formula: moratorium_interest = P * (r / 100) * (M / 12)
        """
        res_cap = calc_repayment_schedule(
            principal=self.principal,
            annual_rate_pct=self.annual_rate_pct,
            tenure_months=self.tenure_months,
            moratorium_months=self.moratorium_months,
            capitalise_moratorium_interest=True,
        )

        # 100,000 * 0.06 * (6 / 12) = 3,000.0
        expected_moratorium_interest = 100000.0 * 0.06 * (6.0 / 12.0)
        expected_effective_principal = self.principal + expected_moratorium_interest

        self.assertAlmostEqual(res_cap["moratorium_interest"], expected_moratorium_interest, places=4)
        self.assertAlmostEqual(res_cap["effective_principal"], expected_effective_principal, places=4)
        self.assertGreater(res_cap["effective_principal"], self.principal)

    def test_case_c_emi_difference(self):
        """Case C — EMI difference:
        For a positive interest rate and non-zero moratorium:
        capitalised_mode_EMI > non_capitalised_mode_EMI assuming the same remaining tenure.
        """
        res_non_cap = calc_repayment_schedule(
            principal=self.principal,
            annual_rate_pct=self.annual_rate_pct,
            tenure_months=self.tenure_months,
            moratorium_months=self.moratorium_months,
            capitalise_moratorium_interest=False,
        )
        res_cap = calc_repayment_schedule(
            principal=self.principal,
            annual_rate_pct=self.annual_rate_pct,
            tenure_months=self.tenure_months,
            moratorium_months=self.moratorium_months,
            capitalise_moratorium_interest=True,
        )

        self.assertGreater(res_cap["monthly_emi"], res_non_cap["monthly_emi"])
        self.assertGreater(res_cap["total_repayment"], res_non_cap["total_repayment"])
        self.assertGreater(res_cap["total_interest"], res_non_cap["total_interest"])
        self.assertAlmostEqual(
            res_cap["emi_difference"],
            res_cap["monthly_emi"] - res_non_cap["monthly_emi"],
            places=4,
        )
        self.assertAlmostEqual(
            res_cap["total_repayment_difference"],
            res_cap["total_repayment"] - res_non_cap["total_repayment"],
            places=4,
        )

    def test_case_d_zero_interest(self):
        """Case D — Zero interest:
        With zero interest, capitalised_principal == original_principal and both modes produce the same EMI.
        """
        res_non_cap = calc_repayment_schedule(
            principal=self.principal,
            annual_rate_pct=0.0,
            tenure_months=self.tenure_months,
            moratorium_months=self.moratorium_months,
            capitalise_moratorium_interest=False,
        )
        res_cap = calc_repayment_schedule(
            principal=self.principal,
            annual_rate_pct=0.0,
            tenure_months=self.tenure_months,
            moratorium_months=self.moratorium_months,
            capitalise_moratorium_interest=True,
        )

        self.assertEqual(res_cap["moratorium_interest"], 0.0)
        self.assertEqual(res_cap["effective_principal"], self.principal)
        self.assertAlmostEqual(res_non_cap["monthly_emi"], res_cap["monthly_emi"], places=4)
        self.assertAlmostEqual(res_non_cap["total_repayment"], res_cap["total_repayment"], places=4)

    def test_case_e_schedule_consistency(self):
        """Case E — Schedule consistency:
        The quarterly schedule must correspond to the selected calculation mode
        and its totals must remain internally consistent.
        """
        for cap in (False, True):
            res = calc_repayment_schedule(
                principal=self.principal,
                annual_rate_pct=self.annual_rate_pct,
                tenure_months=self.tenure_months,
                moratorium_months=self.moratorium_months,
                capitalise_moratorium_interest=cap,
            )

            quarters = res["quarters"]
            total_schedule_amount = sum(q["amount_due"] for q in quarters)

            # Sum of quarterly payments must match total_repayment
            self.assertAlmostEqual(total_schedule_amount, res["total_repayment"], places=2)

            # Moratorium quarters must have amount_due == 0
            moratorium_quarters = [q for q in quarters if q["is_moratorium_only"]]
            self.assertTrue(len(moratorium_quarters) > 0)
            for mq in moratorium_quarters:
                self.assertEqual(mq["amount_due"], 0.0)

            # Each quarter's repayment amount must equal monthly_emi * repayment_months_in_quarter
            for q in quarters:
                expected_due = res["monthly_emi"] * q["repayment_months"]
                self.assertAlmostEqual(q["amount_due"], expected_due, places=2)

    def test_case_f_existing_behavior_and_defaults(self):
        """Case F — Existing behavior:
        Default parameter capitalise_moratorium_interest=False must produce exact existing behavior.
        """
        # Call without 5th argument
        res_default = calc_repayment_schedule(
            self.principal,
            self.annual_rate_pct,
            self.tenure_months,
            self.moratorium_months,
        )
        res_explicit_false = calc_repayment_schedule(
            self.principal,
            self.annual_rate_pct,
            self.tenure_months,
            self.moratorium_months,
            capitalise_moratorium_interest=False,
        )

        self.assertFalse(res_default["capitalise_moratorium_interest"])
        self.assertEqual(res_default["monthly_emi"], res_explicit_false["monthly_emi"])
        self.assertEqual(res_default["total_repayment"], res_explicit_false["total_repayment"])
        self.assertEqual(res_default["effective_principal"], self.principal)
        self.assertIn("you pay nothing during the free period at the start, and no interest is added", res_default["assumption"])

    def test_dynamic_assumption_text(self):
        """Verify dynamic assumption text matches selected mode."""
        res_non_cap = calc_repayment_schedule(
            self.principal, self.annual_rate_pct, self.tenure_months, self.moratorium_months, False
        )
        res_cap = calc_repayment_schedule(
            self.principal, self.annual_rate_pct, self.tenure_months, self.moratorium_months, True
        )

        self.assertIn("no interest is added", res_non_cap["assumption"])
        self.assertIn("simple interest accrues during the free moratorium period and is added to your principal", res_cap["assumption"])


class TestRepaymentAPIEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_api_repayment_default_mode(self):
        """Verify POST /api/repayment-schedule defaults to capitalise_moratorium_interest=False."""
        payload = {
            "principal": 50000.0,
            "annual_rate_pct": 5.0,
            "tenure_months": 36,
            "moratorium_months": 3,
        }
        response = self.client.post("/api/repayment-schedule", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["capitalise_moratorium_interest"])
        self.assertEqual(data["effective_principal"], 50000.0)
        self.assertEqual(data["moratorium_interest"], 0.0)

    def test_api_repayment_capitalised_mode(self):
        """Verify POST /api/repayment-schedule with capitalise_moratorium_interest=True."""
        payload = {
            "principal": 50000.0,
            "annual_rate_pct": 5.0,
            "tenure_months": 36,
            "moratorium_months": 3,
            "capitalise_moratorium_interest": True,
        }
        response = self.client.post("/api/repayment-schedule", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["capitalise_moratorium_interest"])

        # 50,000 * 0.05 * (3 / 12) = 312.5
        expected_interest = 50000.0 * 0.05 * 0.25
        self.assertAlmostEqual(data["moratorium_interest"], expected_interest, places=2)
        self.assertAlmostEqual(data["effective_principal"], 50000.0 + expected_interest, places=2)
        self.assertGreater(data["monthly_emi"], data["baseline_monthly_emi"])
        self.assertGreater(data["emi_difference"], 0.0)


if __name__ == "__main__":
    unittest.main()
