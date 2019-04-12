# -*- coding: utf:8 -*-

from odoo import models, fields, api
import logging


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def _compute_residual(self):
        rs = super(AccountInvoice, self)._compute_residual()

        # ================= Revisar cuando es mas de una factura

        orders = self.mapped("invoice_line_ids").mapped("sale_line_ids").mapped("order_id")
        orders.write(dict(paid_amount=0, payment_state='unpaid'))
        lines = orders.mapped("order_line")
        lines.write(dict(paid_amount=0, payment_state='unpaid'))

        orders = orders.filtered(lambda r: r.state == 'sale')

        invoices = orders.mapped("invoice_ids").filtered(lambda r: r.state in ['open', 'paid'])

        for i in invoices:
            invoice_paid_amount = i.amount_total - i.residual
            for s in i.mapped("invoice_line_ids").mapped("sale_line_ids"):
                amount_pend = s.price_total - s.paid_amount
                # logging.getLogger("____PAGADO___").info("%s ===> %s", invoice_paid_amount, amount_pend)
                if invoice_paid_amount >= amount_pend:
                    s.write(dict(paid_amount=s.price_total, payment_state='paid'))
                    invoice_paid_amount -= amount_pend
                else:
                    paid = s.paid_amount + invoice_paid_amount
                    invoice_paid_amount = 0
                    s.write(dict(paid_amount=paid, payment_state='unpaid'))

        payment_amount = sum([l.paid_amount for l in orders.mapped("order_line")])
        orders.write(dict(paid_amount=payment_amount))
        len_state = orders.mapped("order_line").mapped("payment_state")

        if len(len_state) == 1:
            if len_state[0] == "paid":
                orders.write(dict(payment_state="paid"))

        return rs


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_state = fields.Selection([
        ('unpaid', 'No Pagado'),
        ('paid', 'Pagado')
    ])

    paid_amount = fields.Float(string="Paid Amount")


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    payment_state = fields.Selection([
        ('unpaid', 'No Pagado'),
        ('paid', 'Pagado')
    ])

    paid_amount = fields.Float(string="Paid Amount")


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def post(self):
        rs = super(AccountPayment, self).post()
        # self._compute_sale_payment()
        return rs

    def action_cancel(self):
        rs = super(AccountPayment, self).action_cancel()
        # self._compute_sale_payment()
        return rs


class SaleCommissionWizard(models.TransientModel):
    _name = "sale.commission.wizard"
