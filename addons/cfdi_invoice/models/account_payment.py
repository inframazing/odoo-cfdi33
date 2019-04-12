# -*- coding: utf-8 -*-

import base64
import os
from OpenSSL import crypto
import pytz
import pyqrcode
from xml.etree import ElementTree as ET
from lxml import etree as ET2
from odoo import fields, models, api
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import Warning
import amount_to_text_es_MX
import logging
from suds.client import Client

_log = logging.getLogger("======================= PAYMENT =======================")

_CFDI_FORMAT = '%Y-%m-%dT%H:%M:%S'

NSMAP = {'xsi': 'http://www.w3.org/2001/XMLSchema-instance','cfdi': 'http://www.sat.gob.mx/cfd/3', 'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'}


class AccountPaymentInvoiceCFDI(models.Model):
    _name = 'account.payment.invoice.cfdi'

    name = fields.Many2one('account.invoice', string='Factura',required=True, ondelete='cascade')
    uuid = fields.Char('UUID', related='name.uuid')
    serie = fields.Char('Serie', compute='_get_serie', store=False)
    folio = fields.Char('Folio', compute='_get_folio', store=False)
    metodo_pago = fields.Many2one('sat.metodo.pago', string='Método de pago', related='name.metodo_pago')
    currency_id = fields.Many2one('res.currency', string='Moneda', related='name.currency_id')
    parcialidad = fields.Integer('Parcialidad', required=True)
    saldo_ant = fields.Monetary('Saldo Anterior', required=True)
    pagado = fields.Monetary('Pagado', required=True)
    saldo = fields.Monetary('Saldo Pendiente', compute='_get_saldo', store=False)
    payment_id = fields.Many2one('account.payment', string='Payment', required=True, ondelete='cascade')

    @api.one
    def _get_serie(self):
        self.serie = self.name.number.split(" ")[0]

    @api.one
    def _get_folio(self):
        self.folio = self.name.number.split(" ")[1]

    @api.one
    def _get_saldo(self):
        saldo = self.saldo_ant - self.pagado
        if len(str(saldo)) == 0:
            saldo = 0
        if float(saldo) <= 0:
            saldo = 0
        self.saldo = saldo

class abstractPayments(models.AbstractModel):
    
    _inherit = 'account.abstract.payment'

    fecha_emision = fields.Datetime(string="Fecha de Emision", default=lambda self: fields.Datetime.now())
    fecha_pago = fields.Datetime('Fecha de pago', required=True, default=lambda self: fields.Datetime.now(), copy=False)
    canceled_payment_ids = fields.One2many('account.payment', 'canceled_payment', string='Pagos cancelados relacionados', copy=False)
    cuenta_emisor = fields.Many2one('res.partner.bank', string='Cuenta del emisor')
    banco_emisor = fields.Char('Banco del emisor', related='cuenta_emisor.bank_name', readonly=True)
    rfc_banco_emisor = fields.Char('RFC banco emisor', related='cuenta_emisor.bank_bic', readonly=True)
    numero_operacion = fields.Char('Numero de operación', help='Se puede registrar el número de cheque, número de autorización, '
    + 'número de referencia,\n clave de rastreo en caso de ser SPEI, línea de captura o algún número de referencia \n o '
    + 'identificación análogo que permita identificar la operación correspondiente al pago efectuado.')


class account_register_payments(models.TransientModel):
    
    _inherit = "account.register.payments"

    def get_payment_vals(self):
        return {
            'journal_id': self.journal_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_date': self.payment_date,
            'communication': self.communication,
            'invoice_ids': [(4, inv.id, None) for inv in self._get_invoices()],
            'payment_type': self.payment_type,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_type': self.partner_type,
            'fecha_emision': self.fecha_emision,
            'fecha_pago': self.fecha_pago,
            'canceled_payment_ids': self.canceled_payment_ids,
            'cuenta_emisor': self.cuenta_emisor.id,
            'banco_emisor': self.banco_emisor,
            'rfc_banco_emisor': self.rfc_banco_emisor,
            'numero_operacion': self.numero_operacion,
        }

class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = ['account.payment', 'mail.thread']

    payment_date = fields.Date(string="Fecha de Emision", default=lambda self: fields.Date.today())
    cfdi = fields.Boolean('Timbrado', default=False, readonly=True, copy=False)
    amount_total_text = fields.Char('Total con letra', compute='_get_amount_total_text', store=False)
    forma_pago = fields.Many2one('sat.forma.pago', string='Forma de pago', default=lambda self: self.get_default_id('cfdi_invoice.sat_forma_pago_03'), copy=False)
    uso_cfdi = fields.Many2one('sat.uso.cfdi', string='Uso CFDI (cliente)', default=lambda self: self.get_default_id('cfdi_invoice.sat_uso_cfdi_P01'), readonly=True, copy=False)
    fecha_timbrado = fields.Char('Fecha de Timbrado', readonly=True, copy=False)
    canceled_payment = fields.Many2one('account.payment', string='Pago reemplazo',help='Si este complemento de pago se relaciona con uno previamente cancelado, por favor seleccionelo aquí.', copy=False)
    payment_invoices_ids = fields.One2many('account.payment.invoice.cfdi', 'payment_id', string='Facturas asociadas', copy=False)
    payment_invoices_total = fields.Monetary('Suma de facturas pagadas', readonly=True, copy=False)
    amount_difference = fields.Monetary('Diferencia de monto', readonly=True, copy=False)
    usuario_timbrado = fields.Many2one('res.users', string='Timbrado por', readonly=True, copy=False)
    uuid = fields.Char('Factura UUID', readonly=True, copy=False)
    certificado_emisor = fields.Char('Certificador emisor', readonly=True, copy=False)
    certificado_sat = fields.Char('Certificado sat', readonly=True, copy=False)
    rfc_pac = fields.Char('RFC del PAC', readonly=True, copy=False)
    lugar_expedicion = fields.Char('Lugar de expedición', readonly=True, copy=False)
    sello_digital = fields.Char('Sello digital', readonly=True, copy=False)
    sello_digital_sat = fields.Char('Sello digital SAT', readonly=True, copy=False)
    cad_org_tfd = fields.Char('Cadena Original TFD', readonly=True, copy=False)
    xml_name = fields.Char('Nombre XML', copy=False)
    xml_cfdi = fields.Binary('XML CFDI', readonly=True, copy=False)
    qrcode = fields.Binary('QRCode', readonly=True, copy=False)
    state = fields.Selection(selection_add=[('cancelled', 'Cancelado')])
    move_ids = fields.Many2many("account.move", compute="_compute_moves", store=False)
    banco_receptor = fields.Char('Banco receptor', compute='_compute_banco_receptor')
    cuenta_beneficiario = fields.Char('Cuenta beneficiario', compute='_compute_banco_receptor')
    rfc_banco_receptor = fields.Char('RFC banco receptor', compute='_compute_banco_receptor')
    payment_method_id = fields.Many2one("account.payment.method", default=lambda self: self._compute_default_method())
    

    def _compute_default_method(self):
        return self.env["account.payment.method"].search([('code', '=', 'manual')], limit=1).id

    @api.one
    @api.depends('journal_id')
    def _compute_banco_receptor(self):
        if self.journal_id and self.journal_id.bank_id:
            self.banco_receptor = self.journal_id.bank_id.name
            self.rfc_banco_receptor = self.journal_id.bank_id.bic
        if self.journal_id:
            self.cuenta_beneficiario = self.journal_id.bank_acc_number

    def get_default_id(self, ref):
        try:
            return self.env.ref(ref).id
        except:
            return False

    @api.one
    def _compute_moves(self):
        self.move_ids = self.move_line_ids.mapped("move_id.id")

    @api.multi
    def download_xml(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=account.payment&field=xml_cfdi&id=%s&filename=archivo.xml' % (
                self.id),
            'target': 'self',
        }

    def get_total(self, payment, invoice):
        payment_currency_id = False
        if invoice.type in ('out_invoice', 'in_refund'):
            amount = sum([p.amount for p in payment.matched_debit_ids if p.debit_move_id in invoice.move_id.line_ids])
            amount_currency = sum([p.amount_currency for p in payment.matched_debit_ids if p.debit_move_id in invoice.move_id.line_ids])
            if payment.matched_debit_ids:
                payment_currency_id = all([p.currency_id == payment.matched_debit_ids[0].currency_id for p in payment.matched_debit_ids]) and payment.matched_debit_ids[0].currency_id or False
        elif invoice.type in ('in_invoice', 'out_refund'):
            amount = sum([p.amount for p in payment.matched_credit_ids if p.credit_move_id in invoice.move_id.line_ids])
            amount_currency = sum([p.amount_currency for p in payment.matched_credit_ids if p.credit_move_id in invoice.move_id.line_ids])
            if payment.matched_credit_ids:
                payment_currency_id = all([p.currency_id == payment.matched_credit_ids[0].currency_id for p in payment.matched_credit_ids]) and payment.matched_credit_ids[0].currency_id or False
        if payment_currency_id and payment_currency_id == invoice.currency_id:
            amount_to_show = amount_currency
        else:
            amount_to_show = payment.company_id.currency_id.with_context(date=payment.date).compute(amount, invoice.currency_id)
        if float_is_zero(amount_to_show, precision_rounding=invoice.currency_id.rounding):
            return 0.0
        return amount_to_show

    def compute_payment_invoices(self):
        total_pagos = 0.0
        for rec in self.payment_invoices_ids:
            rec.unlink()
        self.env.cr.commit()
        for invoice in self.invoice_ids:
            pagos_ant = 0.0
            pago_actual = 0.0
            count = 0
            for payment in invoice.payment_move_line_ids:
                if payment.payment_id.id != self.id and payment.payment_id.cfdi:
                    count = count + 1
                    pagos_ant = pagos_ant + self.get_total(payment, invoice)
                elif payment.payment_id.id == self.id:
                    pago_actual = self.get_total(payment, invoice)
            vals = {
                'name': invoice.id,
                'parcialidad': count + 1,
                'pagado': '%.2f' % pago_actual,
                'saldo_ant': invoice.amount_total - pagos_ant,
                'payment_id': self.id
            }
            self.env['account.payment.invoice.cfdi'].create(vals)
            total_pagos = total_pagos + invoice.currency_id.with_context(date=self.payment_date).compute(pago_actual, self.currency_id)
        self.payment_invoices_total = total_pagos
        self.amount_difference = total_pagos - self.amount
        self.env.cr.commit()

    @api.onchange("fecha_emision")
    def onchange_fecha_emision(self):
        if self.env.user.tz:
            timezone = pytz.timezone(self.env.user.tz)
            date = fields.Datetime.from_string(self.fecha_emision).replace(tzinfo=pytz.utc).astimezone(timezone)
        else:
            date = fields.Datetime.from_string(self.fecha_emision)
        self.payment_date = date.strftime("%Y-%m-%d")
        self.fecha_pago = fields.Datetime.from_string(self.fecha_emision)

    @api.multi
    def _get_amount_total_text(self):
        for rec in self:
            rec.amount_total_text = amount_to_text_es_MX.get_amount_to_text(rec.amount, rec.currency_id.name)

    def validations(self):
        warning = u""
        if not float_is_zero(self.amount_difference, precision_rounding=self.currency_id.rounding):
            warning = warning + u"El pago no ha sido aplicado en totalidad a facturas del cliente, por lo que no puede ser timbrado.\n\n"
        for rec in self.payment_invoices_ids:
            if not rec.name.cfdi:
                warning = warning + u"La factura: %s no ha sido timbrada, primero timbrela y después timbre el complemento de pago.\n\n" % rec.name.number
        if not self.env.user.tz or self.env.user.tz == "":
            warning = warning + u"El usuario debe tener configurada la zona horaria para poder timbrar. Para configurarla:\n" \
                                u"Clic en su nombre (parte superior derecha).\n" \
                                u"Clic en preferencias.\n" \
                                u"Seleccionar la zona horaria que se debe utilizar, ejemplo: America/Mexico_City.\n\n"
        if not self.env.user.branch_office or len(self.env.user.branch_office) != 1:
            warning = warning + u"El usuario deber tener asociada la sucursal sobre la que factura.\n\n"
        if not self.env.user.branch_office.partner.zip or self.env.user.branch_office.partner.zip == "":
            warning = warning + u"La dirección de la sucursal debe tener un código postal.\n\n"
        if not self.company_id.vat or (len(self.company_id.vat) != 13 and len(self.company_id.vat) != 12):
            warning = warning + u"El RFC del emisor parece ser invalido.\n\n"
        if not self.partner_id.vat or (len(self.partner_id.vat) != 13 and len(self.partner_id.vat) != 12):
            warning = warning + u"El RFC del receptor parece ser invalido.\n\n"
        if len(self.forma_pago) == 0:
            warning = warning + u"Debe seleccionar la forma de pago.\n\n"
        if len(self.uso_cfdi) == 0:
            warning = warning + u"Debe seleccionar el uso del CFDI.\n\n"
        if warning != "":
            raise Warning(warning)

    def gen_xml(self):
        self.validations()
        timezone = pytz.timezone(self.env.user.tz)
        comprobante = ET.Element('cfdi:Comprobante')
        comprobante.set('xmlns:cfdi', 'http://www.sat.gob.mx/cfd/3')
        comprobante.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        comprobante.set('xsi:schemaLocation', 'http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd http://www.sat.gob.mx/Pagos http://www.sat.gob.mx/sitio_internet/cfd/Pagos/Pagos10.xsd')
        comprobante.set('xmlns:pago10', 'http://www.sat.gob.mx/Pagos')
        comprobante.set('Version', '3.3')
        fecha_factura = fields.Datetime.from_string(
            self.fecha_emision).replace(tzinfo=pytz.utc).astimezone(timezone)
        comprobante.set('Fecha', fecha_factura.strftime(_CFDI_FORMAT))
        comprobante.set('NoCertificado',self.env.user.branch_office.pac_config.no_cer)
        comprobante.set('Certificado', self.env.user.branch_office.pac_config.cer.strip())
        comprobante.set('Moneda', 'XXX')
        comprobante.set('SubTotal', '0')
        comprobante.set('Total', '0')
        comprobante.set('TipoDeComprobante', 'P')
        comprobante.set('LugarExpedicion',self.env.user.branch_office.partner.zip or '')
        if len(self.canceled_payment_ids) > 0:
            cfdi_relacionados = ET.Element('cfdi:CfdiRelacionados')
            cfdi_relacionados.set('TipoRelacion', self.env.ref('cfdi_invoice.sat_tipo_relacion_04').code)
            for cfdis in self.canceled_payment_ids:
                cfdi_relacionado = ET.Element('cfdi:CfdiRelacionado')
                cfdi_relacionado.set('UUID', cfdis.uuid or '')
                cfdi_relacionados.append(cfdi_relacionado)
            comprobante.append(cfdi_relacionados)
        emisor = ET.Element('cfdi:Emisor')
        emisor.set('Rfc', self.company_id.vat or '')
        emisor.set('Nombre', self.company_id.name or '')
        emisor.set('RegimenFiscal', self.company_id.regimen_fiscal or '')
        comprobante.append(emisor)
        receptor = ET.Element('cfdi:Receptor')
        receptor.set('Rfc', self.partner_id.vat or '')
        receptor.set('Nombre', self.partner_id.name or '')
        receptor.set('UsoCFDI', self.uso_cfdi.code)
        comprobante.append(receptor)
        conceptos = ET.Element('cfdi:Conceptos')
        concepto = ET.Element('cfdi:Concepto')
        concepto.set('ClaveProdServ', '84111506')
        concepto.set('ClaveUnidad', 'ACT')
        concepto.set('Cantidad', '1')
        concepto.set('Descripcion', 'Pago')
        concepto.set('ValorUnitario', '0')
        concepto.set('Importe', '0')
        conceptos.append(concepto)
        comprobante.append(conceptos)
        complemento = ET.Element('cfdi:Complemento')
        pagos = ET.Element('pago10:Pagos')
        pagos.set('Version', '1.0')
        pago = ET.Element('pago10:Pago')
        fecha_pago = fields.Datetime.from_string(
            self.fecha_pago).replace(tzinfo=pytz.utc).astimezone(timezone)
        pago.set('FechaPago', fecha_pago.strftime(_CFDI_FORMAT))
        pago.set('FormaDePagoP', self.forma_pago.code)
        pago.set('MonedaP', self.currency_id.name)
        if self.currency_id.name != "MXN":
            pago.set('TipoCambioP', "%.4f" % (1 / self.currency_id.with_context(date=self.fecha_pago).rate))
        pago.set('Monto', "%.2f" % self.amount)
        if self.cuenta_emisor.acc_number != False:
            pago.set('NumOperacion', self.numero_operacion)
            pago.set('RfcEmisorCtaOrd', self.rfc_banco_emisor)
            pago.set('NomBancoOrdExt', self.banco_emisor)
            pago.set('CtaOrdenante', self.cuenta_emisor.acc_number)
            pago.set('RfcEmisorCtaBen', self.rfc_banco_receptor)
            pago.set('CtaBeneficiario', self.cuenta_beneficiario)
        for rec in self.payment_invoices_ids:
            doc = ET.Element('pago10:DoctoRelacionado')
            doc.set('IdDocumento', rec.uuid)
            doc.set('Serie', rec.serie)
            doc.set('Folio', rec.folio)
            doc.set('MonedaDR', rec.currency_id.name)
            doc.set('MetodoDePagoDR', rec.metodo_pago.code)
            doc.set('NumParcialidad', "%s" % rec.parcialidad)
            doc.set('ImpSaldoAnt', "%.2f" % rec.saldo_ant)
            rec_pagado = rec.pagado
            if rec_pagado > rec.saldo_ant:
                rec_pagado = rec.saldo_ant
            doc.set('ImpPagado', "%.2f" % rec_pagado)
            doc.set('ImpSaldoInsoluto', "%.2f" % rec.saldo)
            pago.append(doc)
        pagos.append(pago)
        complemento.append(pagos)
        comprobante.append(complemento)
        xslt_file = os.path.dirname(os.path.realpath(__file__)).replace('models', 'data_sat/cadenaoriginal_3_3.xslt')
        xslt = ET2.parse(xslt_file)
        transform = ET2.XSLT(xslt)
        xml = ET2.fromstring(ET.tostring(comprobante, encoding="UTF-8"))
        cadena_original = "%s" % transform(xml)
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, self.env.user.branch_office.pac_config.key_pem)
        sello = base64.b64encode(crypto.sign(key, cadena_original, 'SHA256'))
        comprobante.set('Sello', sello)
        return ET.tostring(comprobante, encoding="UTF-8")

    def get_cbb(self, msg):
        try:
            code = pyqrcode.create(msg, error='L', mode='binary')
            data = code.png_as_base64_str(scale=10, module_color=[0, 0, 0, 0], background=[0xff, 0xff, 0xff],quiet_zone=1)
        except:
            raise Warning("No fue posible crear el CBB")
        return data

    @api.multi
    def timbrar(self):
        for rec in self:
            rec.compute_payment_invoices()
            pac = self.env.user.branch_office.pac_config
            if not pac or len(pac) == 0:
                raise Warning("Configure los datos del PAC correctamente para poder timbrar.")
            xml = rec.gen_xml()
            result = pac.timbrar_xml(rec, xml)
            if result['validate']:
                xml = result['xml']
                UUID = result['uuid']
                xml_obj = ET2.fromstring(base64.b64decode(xml))
                xml_name = "%s.xml" % UUID
                TFD = xml_obj.find('cfdi:Complemento', NSMAP).find('tfd:TimbreFiscalDigital', NSMAP)
                fecha_timbrado = TFD.attrib['FechaTimbrado']
                certificado_emisor = xml_obj.attrib['NoCertificado']
                certificado_sat = TFD.attrib['NoCertificadoSAT']
                lugar_expedicion = xml_obj.attrib['LugarExpedicion']
                sello_digital = xml_obj.attrib['Sello']
                sello_digital_sat = TFD.attrib['SelloSAT']
                rfc_pac = TFD.attrib['RfcProvCertif']
                url = 'https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx'
                qr_value = '%s?id=%s&re=%s&rr=%s&tt=0&fe=%s' % (url, UUID, self.env.user.company_id.vat, rec.partner_id.vat, sello_digital[-8:])
                qrcode = rec.get_cbb(qr_value)
                xslt_file = os.path.dirname(os.path.realpath(__file__)).replace('models', 'data_sat/cadenaoriginal_TFD_1_1.xslt')
                xslt = ET2.parse(xslt_file)
                transform = ET2.XSLT(xslt)
                cad_org_tfd = '%s' % transform(TFD)
                vals = {
                    'usuario_timbrado': self.env.user.id,
                    'xml_cfdi': xml,
                    'xml_name': xml_name,
                    'uuid': UUID,
                    'fecha_timbrado': fecha_timbrado,
                    'certificado_emisor': certificado_emisor,
                    'certificado_sat': certificado_sat,
                    'rfc_pac': rfc_pac,
                    'lugar_expedicion': lugar_expedicion,
                    'sello_digital': sello_digital,
                    'sello_digital_sat': sello_digital_sat,
                    'qrcode': qrcode,
                    'cad_org_tfd': cad_org_tfd,
                    'cfdi': True
                }
                pac.write({'timbres': pac.timbres + 1})
                rec.write(vals)
            else:
                error = "%s: %s\n" % (result['code'], result['description'] and unicode(result['description'], errors='ignore') or '')
                raise Warning("%s\n%s" %(error, unicode(xml, errors='ignore')))

    @api.multi
    def download_xml(self):
        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/%s/%s/xml_cfdi/%s' % (self._name, self.id, self.xml_name)
        }

    def cancel(self):
        rs = super(AccountPayment, self).cancel()
        self.state = "cancelled"
        return rs

    def action_cancel(self):
        self.cancel()

    @api.multi
    def validate_complete_payment(self):
        self.post()
        x = self.env.ref("cfdi_invoice.account_payment_simple_form_v2")
        return {
            'name': 'Pagos',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'view_id': x.id,
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'view_ids': [(4, x.id, False)]
        }

    @api.multi
    def sent_email(self):
        self.ensure_one()
        template = self.env.ref('cfdi_invoice.email_template_edi_payment', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='account.payment',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            force_email=True
        )
        return {
            'name': 'Compose Email',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def onchange_template_id(self, template_id, composition_mode, model, res_id):
        rs = super(MailComposer, self).onchange_template_id(
            template_id, composition_mode, model, res_id)
        if model == "account.payment":
            payment = self.env[model].browse(res_id)
            if payment.cfdi:
                xml = payment.xml_cfdi
                vals = dict(
                    name=payment.name,
                    datas=xml,
                    datas_fname='%s.xml' % (payment.name),
                    res_model='mail.compose.message',
                    res_id=0,
                    type='binary'
                )
                a = self.env['ir.attachment'].create(vals)
                rs['value']["attachment_ids"] = rs['value']["attachment_ids"] + \
                    [(4, a.id, False)]
        return rs
