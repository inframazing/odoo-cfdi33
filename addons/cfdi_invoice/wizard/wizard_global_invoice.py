# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.exceptions import Warning
import logging

class globalInvoice(models.TransientModel):
    
    _name = "wizard.global.invoice"

    filterDate = fields.Selection(
    	[
    		('day','Por dia'), 
    		('week','Por semana'),
    		('month','Por mes')
    	],'Generar factura',default='month',required=True)
    branch_id  = fields.Many2one('company.branch.office', string='Sucursal', required=True)
    date = fields.Date(string='Dia')
    month = fields.Selection(
    	[
	    	(1, 'Enero'), 
	    	(2, 'Febrero'), 
	    	(3, 'Marzo'),
	    	(4, 'Abril'),
	    	(5, 'Mayo'), 
	    	(6, 'Junio'), 
	    	(7, 'Julio'), 
	    	(8, 'Agosto'), 
	    	(9, 'Septiembre'), 
	    	(10, 'Octubre'),
	    	(11, 'Noviembre'),
	    	(12, 'Diciembre')
	    ],'Mes')

    sale_order_ids = fields.One2many('wizard.global.invoice.line', 'wizard_order_id', string='Pedidos')

    def getOrders(self):
    	sales = self.env['sale.order'].search(['&',('partner_id.vat','=','XAXX010101000'),('invoice_status', '=', 'to invoice')])
    	sale = []
        for s in sales:
        	sale.append((0, False, {
        		'order_id': s.id
            }))
        
        sale.insert(0, (5, 0, 0))
        
        self.sale_order_ids = sale
        
        return {
            'name': 'Asistente para Elaborar la Factura Global',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'wizard.global.invoice',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'target': 'new'       
        }
    
    def create_invoice(self):
        order = self.env['sale.order'].browse(3)
        inv_obj = self.env['account.invoice']
        '''account_id = False
        if self.product_id.id:
            account_id = self.product_id.property_account_income_id.id or self.product_id.categ_id.property_account_income_categ_id.id
        if not account_id:
            inc_acc = ir_property_obj.get('property_account_income_categ_id', 'product.category')
            account_id = order.fiscal_position_id.map_account(inc_acc).id if inc_acc else False
        if not account_id:
            raise Warning('There is no income account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.') %(self.product_id.name)'''
        
        invoice = inv_obj.create({
	        'name': order.client_order_ref or order.name,
	        'origin': order.name,
	        'type': 'out_invoice',
	        'reference': False,
	        'account_id': order.partner_id.property_account_receivable_id.id,
	        'partner_id': order.partner_invoice_id.id,
	        'invoice_partner': order.partner_invoice_id.id,
	        'partner_shipping_id': order.partner_shipping_id.id,
	        'invoice_line_ids': [(0, 0, {
	            'name': 'VENTA',
	            'origin': order.name,
	            'account_id': 27,
	            'price_unit': 100,
	            'quantity': 1.0,
	            'discount': 0.0,
	            'uom_id': 23,
	            'product_id': 2,
	            #'sale_line_ids': [(6, 0, [so_line.id])],
	            #'invoice_line_tax_ids': [(6, 0, tax_ids)],
	            'account_analytic_id': order.project_id.id or False,
	        })],
	        'currency_id': order.pricelist_id.currency_id.id,
	        'payment_term_id': order.payment_term_id.id,
	        'fiscal_position_id': order.fiscal_position_id.id or order.partner_id.property_account_position_id.id,
	        'team_id': order.team_id.id,
	        'user_id': order.user_id.id,
	        'comment': order.note,
        })
        invoice.compute_taxes()
        return invoice


class globalInvoiceLine(models.TransientModel):
    
    _name = "wizard.global.invoice.line"


    wizard_order_id = fields.Many2one("wizard.global.invoice")

    order_id     = fields.Many2one('sale.order', string='Pedido')
    date_order   = fields.Datetime(string="Fecha",related='order_id.date_order',   store=True, readonly=True)
    partner_id   = fields.Many2one(string="Cliente",related='order_id.partner_id', store=True, readonly=True)
    user_id      = fields.Many2one(string="Vendedor",related='order_id.user_id',   store=True, readonly=True)
    amount_total = fields.Monetary(string="Total",related='order_id.amount_total', store=True, readonly=True)
    invoice_status = fields.Selection(related='order_id.invoice_status', store=True, readonly=True)
    currency_id    = fields.Many2one(related='order_id.currency_id', store=True, string='Currency', readonly=True)

class SaleAdvancePaymentInv(models.TransientModel):
    
    _inherit = 'sale.advance.payment.inv'

    @api.multi
    def _create_invoice(self, order, so_line, amount):
    	logging.getLogger("==DG== ========================").info('_create_invoice')
    	return super(SaleAdvancePaymentInv,self)._create_invoice(self, order, so_line, amount)