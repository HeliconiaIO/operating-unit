from odoo.tests.common import TransactionCase


class TestAccountBankStatementLine(TransactionCase):
    def setUp(self):
        super().setUp()
        # Create a partner
        self.partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "email": "test@example.com",
            }
        )

        # Create an operating unit
        self.operating_unit = self.env["operating.unit"].create(
            {
                "name": "Test OU",
                "code": "TEST",
                "partner_id": self.partner.id,
            }
        )

        # Create accounts
        self.account_receivable = self.env["account.account"].create(
            {
                "name": "Test Receivable Account",
                "code": "TEST1",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )

        self.account_revenue = self.env["account.account"].create(
            {
                "code": "X2020",
                "name": "Product Sales - (test)",
                "account_type": "income",
            }
        )

        # Create tax accounts
        self.tax_account = self.env["account.account"].create(
            {
                "name": "Tax Account",
                "code": "TAX",
                "account_type": "liability_current",
                "reconcile": False,
            }
        )

        # Create a journal
        self.journal = self.env["account.journal"].create(
            {
                "name": "Test Journal",
                "type": "sale",
                "code": "TESTJ",
                "default_account_id": self.account_revenue.id,
            }
        )

        self.currency = self.env["res.currency"].create(
            {
                "name": "C",
                "symbol": "C",
                "rounding": 0.01,
                "currency_unit_label": "Curr",
                "rate": 1,
            }
        )

        # Get cash basis tax account
        self.cash_basis_base_account = self.env["account.account"].create(
            {
                "name": "Cash Basis Base Account",
                "code": "CBBA",
                "account_type": "liability_current",
                "reconcile": False,
            }
        )

        # Create a tax for cash basis tests with required fields
        self.tax_line = self.env["account.tax"].create(
            {
                "name": "Test Tax",
                "amount": 15.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "tax_exigibility": "on_payment",
                "cash_basis_transition_account_id": self.cash_basis_base_account.id,
                "invoice_repartition_line_ids": [
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": self.tax_account.id,
                        },
                    ),
                ],
                "refund_repartition_line_ids": [
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": self.tax_account.id,
                        },
                    ),
                ],
            }
        )

        analytic_plan = self.env["account.analytic.plan"].create(
            {"name": "Plan with Tax details"}
        )
        self.analytic_account = self.env["account.analytic.account"].create(
            {
                "name": "Analytic account with Tax details",
                "plan_id": analytic_plan.id,
                "company_id": False,
            }
        )

        # Create analytic distribution
        self.analytic_distribution = {str(self.analytic_account.id): 100}

        # Create a move with balanced entries
        self.move = self.env["account.move"].create(
            {
                "name": "Test Move",
                "move_type": "entry",
                "journal_id": self.journal.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Debit Line",
                            "account_id": self.account_receivable.id,
                            "operating_unit_id": self.operating_unit.id,
                            "partner_id": self.partner.id,
                            "debit": 100.0,
                            "credit": 0.0,
                            "amount_currency": 100.0,
                            "currency_id": self.env.company.currency_id.id,
                            "analytic_distribution": self.analytic_distribution,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Credit Line",
                            "account_id": self.account_revenue.id,
                            "operating_unit_id": self.operating_unit.id,
                            "partner_id": self.partner.id,
                            "debit": 0.0,
                            "credit": 100.0,
                            "amount_currency": -100.0,
                            "currency_id": self.env.company.currency_id.id,
                            "analytic_distribution": self.analytic_distribution,
                        },
                    ),
                ],
            }
        )

    def test_prepare_cash_basis_base_line_vals(self):
        """Test operating unit propagation in cash basis base line"""
        reconcile = self.env["account.partial.reconcile"]
        move_line = self.move.line_ids.filtered(lambda x: x.debit > 0)
        result = reconcile._prepare_cash_basis_base_line_vals(move_line, 100.0, 100.0)

        self.assertEqual(
            result["operating_unit_id"],
            self.operating_unit.id,
            "Operating unit not correctly set on cash basis base line",
        )

    def test_prepare_cash_basis_counterpart_base_line_vals(self):
        """Test operating unit propagation in cash basis counterpart base line"""
        reconcile = self.env["account.partial.reconcile"]
        base_vals = {
            "operating_unit_id": self.operating_unit.id,
            "name": "Test",
            "debit": 100.0,
            "credit": 0.0,
            "account_id": self.account_receivable.id,
            "partner_id": self.partner.id,
            "amount_currency": 100.0,
            "currency_id": self.env.company.currency_id.id,
            "analytic_distribution": self.analytic_distribution,
        }

        result = reconcile._prepare_cash_basis_counterpart_base_line_vals(base_vals)

        self.assertEqual(
            result["operating_unit_id"],
            self.operating_unit.id,
            "Operating unit not correctly set on cash basis counterpart base line",
        )

    def test_prepare_cash_basis_tax_line_vals(self):
        """Test operating unit propagation in cash basis tax line"""
        reconcile = self.env["account.partial.reconcile"]
        move_line = self.move.line_ids.filtered(lambda x: x.debit > 0)
        result = reconcile._prepare_cash_basis_tax_line_vals(move_line, 15.0, 15.0)

        self.assertEqual(
            result["operating_unit_id"],
            self.operating_unit.id,
            "Operating unit not correctly set on cash basis tax line",
        )

    def test_prepare_cash_basis_counterpart_tax_line_vals(self):
        """Test operating unit propagation in cash basis counterpart tax line"""
        reconcile = self.env["account.partial.reconcile"]
        tax_repartition_line = self.tax_line.invoice_repartition_line_ids.filtered(
            lambda x: x.repartition_type == "tax"
        )

        # Ensure all required keys are present in tax_vals
        tax_vals = {
            "operating_unit_id": self.operating_unit.id,
            "name": "Test Tax",
            "debit": 15.0,
            "credit": 0.0,
            "account_id": self.tax_account.id,
            "partner_id": self.partner.id,
            "tax_repartition_line_id": tax_repartition_line.id,
            "analytic_distribution": self.analytic_distribution,
            "amount_currency": 15.0,  # Add the missing key
            "currency_id": self.currency.id,  # Ensure currency_id is set
        }
        # Call the method under test
        result = reconcile._prepare_cash_basis_counterpart_tax_line_vals(
            tax_repartition_line, tax_vals
        )

        # Verify the expected result
        self.assertEqual(
            result["operating_unit_id"],
            self.operating_unit.id,
            "Operating unit not correctly set on cash basis counterpart tax line",
        )
