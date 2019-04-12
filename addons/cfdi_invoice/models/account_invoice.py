# -*- coding: utf-8 -*-

import base64
import os
import urllib
from OpenSSL import crypto
import pytz
import pyqrcode
import png
from xml.etree import ElementTree as ET
from lxml import etree as ET2
from odoo import fields, models, api
from odoo.exceptions import Warning
import amount_to_text_es_MX
import logging
from suds.client import Client

_CFDI_FORMAT = '%Y-%m-%dT%H:%M:%S'

NSMAP = {'xsi': 'http://www.w3.org/2001/XMLSchema-instance', 'cfdi': 'http://www.sat.gob.mx/cfd/3',
         'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'}

_log = logging.getLogger("========= CFDI =========")


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.onchange("partner_id")
    def onchange_partner_id(self):
        self.invoice_partner = self.partner_id.name

    @api.depends('partner_id')
    def _compute_get_name(self):
        return self.partner_id.name

    date_invoice = fields.Date('Fecha factura', readonly=True, states={'draft': [('readonly', False)]},
                               default=lambda self: fields.Date.today(), copy=False)
    cfdi = fields.Boolean('Generado el CFDI', default=False, readonly=True, copy=False)
    usuario_timbrado = fields.Many2one('res.users', 'Timbrado por', readonly=True, copy=False)
    fecha_timbrado = fields.Char('Fecha de Timbrado', readonly=True, copy=False)
    tipo_comprobante = fields.Selection([('I', 'Ingreso'), ('E', 'Egreso')], string='Tipo de comprobante',
                                        compute='_compute_tipo_comprobante', store=False)
    forma_pago = fields.Many2one('sat.forma.pago', string='Forma de pago', readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 default=lambda self: self.get_default_id('cfdi_invoice.sat_forma_pago_03'))
    metodo_pago = fields.Many2one('sat.metodo.pago', string='Método de pago', readonly=True,
                                  states={'draft': [('readonly', False)]},
                                  default=lambda self: self.get_default_id('cfdi_invoice.sat_metodo_pago_PPD'))
    uso_cfdi = fields.Many2one('sat.uso.cfdi', string='Uso CFDI (cliente)', readonly=True,
                               states={'draft': [('readonly', False)]},
                               default=lambda self: self.get_default_id('cfdi_invoice.sat_uso_cfdi_P01'))
    tipo_relacion = fields.Many2one('sat.tipo.relacion', string='Tipo relación', copy=False)
    cfdis_relacionados = fields.Many2many('account.invoice', relation='account_invoice_cfdi_rel', column1='invoice_id',
                                          column2='invoice_id_rel', string='CFDIs Relacionados', copy=False)
    amount_total_text = fields.Char('Total con letra', compute='_get_amount_total_text', store=False)
    uuid = fields.Char('Factura UUID', readonly=True, copy=False)
    certificado_emisor = fields.Char('Certificador emisor', readonly=True, copy=False)
    certificado_sat = fields.Char('Certificado sat', readonly=True, copy=False)
    rfc_pac = fields.Char('RFC del PAC', readonly=True, copy=False)
    lugar_expedicion = fields.Char('Lugar de expedición', readonly=True, copy=False)
    sello_digital = fields.Char('Sello digital', readonly=True, copy=False)
    sello_digital_sat = fields.Char('Sello digital SAT', readonly=True, copy=False)
    cad_org_tfd = fields.Char('Cadena Original TFD', readonly=True, copy=False)
    xml_name = fields.Char('Nombre XML', readonly=True, copy=False)
    xml_cfdi = fields.Binary('XML CFDI', readonly=True, copy=False)
    qrcode = fields.Binary('QRCode', readonly=True, copy=False)
    debug_xml = fields.Text('Debug XML', readonly=True, copy=False)
    currency_exchange = fields.Float(string="Currency Exchange", compute="_compute_currency_exchange", store=False,
                                     digits=(18, 6))
    xml_acuse = fields.Binary('XML ACUSE', readonly=True, copy=False)
    fecha_cancelacion = fields.Char('Fecha de cancelación', readonly=True, copy=False)
    invoice_partner = fields.Char(string='Razón Social', default=lambda self: self._compute_get_name(), readonly=False,
                                  copy=False)
    partner_vat = fields.Char(related="partner_id.vat")
    status_cancelacion = fields.Selection(
        [('valida', 'Valida'), ('pendiente', 'Pendiente'), ('cancelado', 'Cancelado')], string='Status Cancelación')

    def _get_exchange_rate(self):
        date = fields.Datetime.from_string(self.date_invoice) or fields.Datetime.from_string(fields.Datetime.now())
        x = self.currency_id.with_context(dict(date=date))
        rate = x.rate
        return 1 / rate if rate > 0 else 1

    @api.onchange("currency_id", "date_invoice")
    def _onchange_currency_date(self):
        self.currency_exchange = self._get_exchange_rate()

    @api.one
    @api.depends("currency_id")
    def _compute_currency_exchange(self):
        self.currency_exchange = self._get_exchange_rate()

    def get_default_id(self, ref):
        try:
            return self.env.ref(ref).id
        except:
            return False

    @api.multi
    def invoice_print(self):
        self.ensure_one()
        self.sent = True
        return self.env['report'].get_action(self, 'cfdi_invoice.invoice_report_template')

    @api.onchange('payment_term_id')
    def onchange_payment_term(self):
        if self.payment_term_id:
            count = 0
            for term in self.payment_term_id.line_ids:
                count += term.days
            if count == 0:
                self.metodo_pago = self.env.ref('cfdi_invoice.sat_metodo_pago_PUE').id
            else:
                self.metodo_pago = self.env.ref('cfdi_invoice.sat_metodo_pago_PPD').id

    @api.onchange('partner_id')
    def onchange_partner(self):
        if self.partner_id:
            if self.partner_id.forma_pago:
                self.forma_pago = self.partner_id.forma_pago.id
            if self.partner_id.metodo_pago:
                self.metodo_pago = self.partner_id.metodo_pago.id
            if self.partner_id.uso_cfdi:
                self.uso_cfdi = self.partner_id.uso_cfdi.id

    @api.multi
    def _get_amount_total_text(self):
        for rec in self:
            rec.amount_total_text = amount_to_text_es_MX.get_amount_to_text(rec.amount_total, rec.currency_id.name)

    @api.multi
    def _compute_tipo_comprobante(self):
        for rec in self:
            rec.tipo_comprobante = 'I' if rec.type == 'out_invoice' else 'E'

    @api.multi
    def action_invoice_open(self):
        code = self.env.user.branch_office.invoice_sequence.code
        if not code or code == '':
            raise Warning(
                'El usuario actual debe tener relacionada una sucursal y la sucursal una secuencia de facturación.')
        for rec in self:
            if rec.type == 'out_invoice':
                if (not rec.number or rec.number == '/') and (not rec.move_name or rec.move_name == '/'):
                    move_name = self.env['ir.sequence'].next_by_code(code)
                    rec.write({'move_name': move_name})
                self._cr.commit()
        return super(AccountInvoice, self).action_invoice_open()

    def validations(self):
        warning = u""
        if len(self.number.split(' ')) != 2:
            warning = warning + u"Los números de factura deben tener la forma 'Serie Folio'. Ej. 'A 0001'. Configure correctamente la secuencia.\n\n"
        if not self.env.user.tz or self.env.user.tz == "":
            warning = warning + u"El usuario debe tener configurada la zona horaria para poder timbrar. Para configurarla:\n" \
                                u"Clic en su nombre (parte superior derecha).\n" \
                                u"Clic en preferencias.\n" \
                                u"Seleccionar la zona horaria que se debe utilizar, ejemplo: America/Mexico_City.\n\n"
        if not self.env.user.branch_office or len(self.env.user.branch_office) != 1:
            warning = warning + u"El usuario deber tener asociada la sucursal sobre la que factura.\n\n"
        if not self.user_id.branch_office.partner.zip or self.user_id.branch_office.partner.zip == "":
            warning = warning + u"La dirección de la sucursal debe tener un código postal.\n\n"
        if not self.company_id.vat or (len(self.company_id.vat) != 13 and len(self.company_id.vat) != 12):
            warning = warning + u"El RFC del emisor parece ser invalido.\n\n"
        if not self.partner_id.vat or (len(self.partner_id.vat) != 13 and len(self.partner_id.vat) != 12):
            warning = warning + u"El RFC del receptor parece ser invalido.\n\n"
        if self.tipo_comprobante == "":
            warning = warning + u"El tipo de comprobante no fue fijado correctamente.\n\n"
        if len(self.forma_pago) == 0:
            warning = warning + u"Debe seleccionar la forma de pago.\n\n"
        if len(self.metodo_pago) == 0:
            warning = warning + u"Debe seleccionar el metodo de pago.\n\n"
        if len(self.uso_cfdi) == 0:
            warning = warning + u"Debe seleccionar el uso de que dará el cliente al CFDI.\n\n"
        if warning != "":
            raise Warning(warning)

    def gen_xml(self):
        self.validations()
        number = self.number.split(' ')
        comprobante = ET.Element('cfdi:Comprobante')
        comprobante.set('xmlns:cfdi', 'http://www.sat.gob.mx/cfd/3')
        comprobante.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        comprobante.set('xsi:schemaLocation',
                        'http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd')
        comprobante.set('Version', '3.3')
        comprobante.set('Serie', number[0])
        comprobante.set('Folio', number[1])
        timezone = pytz.timezone(self.env.user.tz)
        fecha_factura = fields.Datetime.from_string(self.date_invoice).replace(tzinfo=pytz.utc).astimezone(timezone)
        comprobante.set('Fecha', fecha_factura.strftime(_CFDI_FORMAT))
        comprobante.set('NoCertificado', self.env.user.branch_office.pac_config.no_cer)
        comprobante.set('Certificado', self.env.user.branch_office.pac_config.cer.strip())
        comprobante.set('Moneda', self.currency_id.name or '')
        if self.currency_id.name != 'MXN':
            comprobante.set('TipoCambio', '%.2f' % self.currency_exchange)
        comprobante.set('TipoDeComprobante', self.tipo_comprobante or '')
        comprobante.set('FormaPago', self.forma_pago.code)
        comprobante.set('MetodoPago', self.metodo_pago.code)
        comprobante.set('LugarExpedicion', self.env.user.branch_office.partner.zip or '')
        if len(self.tipo_relacion) > 0:
            cfdi_relacionados = ET.Element('cfdi:CfdiRelacionados')
            cfdi_relacionados.set('TipoRelacion', self.tipo_relacion.code)
            for cfdis in self.cfdis_relacionados:
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
        if self.partner_id.vat != 'XAXX010101000':
            receptor.set('Nombre', self.partner_id.name or '')
        else:
            receptor.set('Nombre', self.invoice_partner or '')
        receptor.set('UsoCFDI', self.uso_cfdi.code)
        comprobante.append(receptor)
        conceptos = ET.Element('cfdi:Conceptos')
        sum_descuentos = 0.00

        sum_importes = 0.00

        for l in self.invoice_line_ids:

            taxes = l.invoice_line_tax_ids
            price_unit = taxes.compute_all(l.price_unit).get("total_excluded", 0)
            price_unit = "%.6f" % float(price_unit)
            price_unit = float(price_unit)

            # imp_amount_taxes = l.invoice_line_tax_ids.compute_all(price_unit)

            # logging.getLogger("OK............").info(price_unit)
            # raise Warning("Erro 3.......")

            importe = price_unit * l.quantity
            importe = '%.2f' % importe

            concepto = ET.Element('cfdi:Concepto')
            concepto.set('ClaveProdServ', l.product_id.sat_category.code or '')
            concepto.set('ClaveUnidad', l.uom_id.sat_code or '')
            concepto.set('Unidad', l.uom_id.name or '')
            num_id = l.product_id.default_code or l.product_id.sat_category.code or ''
            if len(num_id) > 0:
                concepto.set('NoIdentificacion', num_id)
            concepto.set('Cantidad', '%.6f' % l.quantity)
            concepto.set('Descripcion', l.name or '')
            if l.discount > 0:
                descuento = ((l.quantity * l.price_unit) * l.discount) / 100.0
                descuento = '%.2f' % (descuento)

                sum_descuentos = sum_descuentos + float(descuento)
                concepto.set('Descuento', '%.2f' % float(descuento))
            concepto.set('ValorUnitario', '%.6f' % price_unit)
            concepto.set('Importe', '%.2f' % float(importe))

            sum_importes += float(importe)

            impuestos = ET.Element('cfdi:Impuestos')
            traslados = ET.Element('cfdi:Traslados')
            retenciones = ET.Element('cfdi:Retenciones')
            for i in l.invoice_line_tax_ids:
                i_amount = i.amount if i.amount >= 0.0 else -i.amount
                if i.amount < 0.0:
                    impuesto = ET.Element('cfdi:Retencion')
                else:
                    impuesto = ET.Element('cfdi:Traslado')
                impuesto.set('Base', '%.6f' % l.price_subtotal)
                impuesto.set('Impuesto', i.impuesto or '')
                impuesto.set('TipoFactor', i.tipo_factor or '')
                impuesto.set('TasaOCuota', '%.6f' % (i_amount / 100.0 if i.tipo_factor == 'Tasa' else i_amount))
                impuesto.set('Importe',
                             '%.6f' % (l.price_subtotal * i_amount / 100.0 if i.tipo_factor == 'Tasa' else i_amount))
                if i.amount < 0.0:
                    retenciones.append(impuesto)
                else:
                    traslados.append(impuesto)
            if len(traslados) > 0:
                impuestos.append(traslados)
            if len(retenciones) > 0:
                impuestos.append(retenciones)
            concepto.append(impuestos)
            conceptos.append(concepto)
        comprobante.append(conceptos)
        impuestos = ET.Element('cfdi:Impuestos')
        traslados = ET.Element('cfdi:Traslados')
        retenciones = ET.Element('cfdi:Retenciones')
        sum_traslados = 0.0
        sum_retenciones = 0.0
        for i in self.tax_line_ids:
            i_amount = i.tax_id.amount if i.tax_id.amount >= 0.0 else -i.tax_id.amount
            importe = i_amount * i.base / 100.0 if i.tax_id.tipo_factor == 'Tasa' else i_amount
            if i.tax_id.amount < 0.0:
                sum_retenciones += importe
                impuesto = ET.Element('cfdi:Retencion')
            else:
                sum_traslados += importe
                impuesto = ET.Element('cfdi:Traslado')
                impuesto.set('TipoFactor', i.tax_id.tipo_factor or '')
                impuesto.set('TasaOCuota', '%.6f' % (i_amount / 100.0 if i.tax_id.tipo_factor == 'Tasa' else i_amount))
            impuesto.set('Impuesto', i.tax_id.impuesto or '')
            impuesto.set('Importe', '%.2f' % importe)
            if i.tax_id.amount < 0.0:
                retenciones.append(impuesto)
            else:
                traslados.append(impuesto)
        if abs(sum_traslados) > 0 or len(traslados) > 0:
            impuestos.set('TotalImpuestosTrasladados', '%.2f' % sum_traslados)
        if abs(sum_retenciones) > 0 or len(retenciones) > 0:
            impuestos.set('TotalImpuestosRetenidos', '%.2f' % sum_retenciones)
        if len(retenciones):
            impuestos.append(retenciones)
        if len(traslados):
            impuestos.append(traslados)

        sub_total = sum_importes
        total = sub_total + sum_traslados - sum_retenciones - sum_descuentos

        if sum_descuentos > 0.0:
            comprobante.set('Descuento', '%.2f' % sum_descuentos)
            # sub_total += sum_descuentos

        comprobante.set('SubTotal', '%.2f' % (sub_total))
        comprobante.set('Total', '%.2f' % total)
        comprobante.append(impuestos)
        xslt_file = os.path.dirname(os.path.realpath(__file__)).replace('models', 'data_sat/cadenaoriginal_3_3.xslt')
        xslt = ET2.parse(xslt_file)
        transform = ET2.XSLT(xslt)
        xml = ET2.fromstring(ET.tostring(comprobante, encoding="UTF-8"))
        cadena_original = "%s" % transform(xml)
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, self.env.user.branch_office.pac_config.key_pem)
        sello = base64.b64encode(crypto.sign(key, cadena_original, 'SHA256'))
        comprobante.set('Sello', sello)
        debug_xml = ET.tostring(comprobante, encoding="UTF-8")
        self.write({'debug_xml': debug_xml})
        self.env.cr.commit()
        return debug_xml

    def get_cbb(self, msg):
        try:
            code = pyqrcode.create(msg, error='Q', mode='binary')
            data = code.png_as_base64_str(scale=10, module_color=[0, 0, 0, 0], background=[0xff, 0xff, 0xff],
                                          quiet_zone=1)
        except:
            raise Warning("No fue posible crear el CBB")
        return data

    @api.multi
    def timbrar(self):
        for rec in self:
            pac = self.env.user.branch_office.pac_config
            if not pac or len(pac) == 0:
                raise Warning("Configure los datos del PAC correctamente para poder timbrar.")
            xml = rec.gen_xml()
            result = pac.timbrar_xml(rec, xml)
            if result['validate']:
                xml = result['xml']
                xml_obj = ET2.fromstring(base64.b64decode(xml))
                xml_name = "factura_%s.xml" % rec.number.replace(' ', '_')
                UUID = result['uuid']
                TFD = xml_obj.find('cfdi:Complemento', NSMAP).find('tfd:TimbreFiscalDigital', NSMAP)
                fecha_timbrado = TFD.attrib['FechaTimbrado']
                certificado_emisor = xml_obj.attrib['NoCertificado']
                certificado_sat = TFD.attrib['NoCertificadoSAT']
                lugar_expedicion = xml_obj.attrib['LugarExpedicion']
                sello_digital = xml_obj.attrib['Sello']
                sello_digital_sat = TFD.attrib['SelloSAT']
                rfc_pac = TFD.attrib['RfcProvCertif']
                url = 'https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx'
                qr_value = '%s?id=%s&re=%s&rr=%s&tt=0&fe=%s' % (
                    url, UUID, rec.company_id.vat, rec.partner_id.vat, sello_digital[-8:])
                qrcode = rec.get_cbb(qr_value)
                xslt_file = os.path.dirname(os.path.realpath(__file__)).replace('models',
                                                                                'data_sat/cadenaoriginal_TFD_1_1.xslt')
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
                self.message_post(body=result['description'])
            else:
                error = "%s: %s\n" % (
                    result['code'], result['description'] and unicode(result['description'], errors='ignore') or '')
                raise Warning("%s\n%s" % (error, unicode(xml, errors='ignore')))

    @api.multi
    def download_xml(self):
        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/%s/%s/xml_cfdi/%s' % (self._name, self.id, self.xml_name.replace('/', '-'))
        }

    @api.multi
    def cancel_cfdi(self):
        if self.cfdi and len(self.uuid.split('-')) == 5:
            pac = self.env.user.branch_office.pac_config
            if not pac or len(pac) == 0:
                raise Warning("Configure los datos del PAC correctamente para poder cancelar.")

            logging.getLogger("________________CANCELA______________").info(self.amount_total)
            amount_total = self.amount_total
            if self.id == 24:
                amount_total = 19800.00

            logging.getLogger("_____________params_____").info((self.partner_id.vat, amount_total, self.uuid))

            result = pac.cancelar_cfdi(self.partner_id.vat, amount_total, self.uuid)
            if not result['validate']:
                self.message_post(body="Código: %s\n%s" % (result['code'], result['description']))
                return False
            pac.cancelaciones = pac.cancelaciones + 1
            self.message_post(body="Código: %s\n%s" % (result['code'], result['description']))
            self.write({'status_cancelacion': 'pendiente'})
            return False
        else:
            self.message_post(body="Se cancela la factura sin CFDI previo.")
            return True

    @api.multi
    def consultar_status(self):
        inv = self.env['account.invoice'].search([('status_cancelacion', '=', 'pendiente')])

        amount_total = self.amount_total

        if self.id == 24:
            amount_total = 19800.00

        for fa in inv:
            pac = self.env.user.branch_office.pac_config
            invoice = {
                'receptor': fa.partner_id.vat,
                'total': amount_total,
                'uuid': fa.uuid,
            }

            logging.getLogger("________params_________").info(invoice)

            result = pac.consultar_status(invoice)
            if result['EstatusCancelacion'] != 'En proceso' and result['estado'] == 'Cancelado':
                fa.write({'status_cancelacion': 'cancelado'})
                fa.action_cancel()
                self.message_post(body="Código: %s\n%s" % (result['code'], result['description']))
            else:
                logging.getLogger("_______cancelacion_______").info(result)

    @api.multi
    def action_invoice_cancel(self):
        x = False
        try:
            x = self.cancel_cfdi()
        except:
            self.message_post(body='No se pudo cancelar el CFDI de la factura')
            self.env.cr.commit()

        if x:
            super(AccountInvoice, self).action_invoice_cancel()

    def timbrar_masivo(self, invoice_ids):
        for record in self.env["account.invoice"].browse(invoice_ids):
            if record.cfdi != True and (record.state != 'draft' and record.state != 'cancel'):
                record.timbrar()

    @api.multi
    def download_acuse(self):
        if self.cfdi and len(self.uuid.split('-')) == 5:
            pac = self.env.user.branch_office.pac_config
            if not pac or len(pac) == 0:
                raise Warning("Configure los datos del PAC correctamente para obtener el acuse.")
            result = pac.descargar_acuse(self.uuid)
            if not result['validate']:
                self.message_post(body="Error de acuse de cancelación CFDI.\nCódigo: %s\n%s" % (
                    result['code'], result['description']))
                return False
            xml = result['xml']
            xml_obj = ET2.fromstring(base64.b64decode(xml))
            fecha_cancelado = ""
            for child in xml_obj:
                body = child.getchildren()
                cancelaCfdResponse = body[0]
                cancelaCfdResult = cancelaCfdResponse.getchildren()
                cancela = cancelaCfdResult[0]
                fecha_cancelado = cancela.attrib['Fecha']
            self.write({
                'xml_acuse': xml,
                'fecha_cancelacion': fecha_cancelado
            })
            self.env.cr.commit()
            return {
                'type': 'ir.actions.act_url',
                'url': 'web/content/%s/%s/xml_acuse/%s' % (self._name, self.id, self.xml_name.replace('/', '-'))
            }

    @api.multi
    def action_invoice_sent(self):
        self.ensure_one()
        template = self.env.ref('cfdi_invoice.email_template_edi_invoice_v2', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='account.invoice',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            force_email=True
        )
        return {
            'name': 'Send Invoice',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    product_id = fields.Many2one(required=True)
    uom_id = fields.Many2one(required=True)
    price_unit = fields.Monetary()


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def onchange_template_id(self, template_id, composition_mode, model, res_id):
        rs = super(MailComposer, self).onchange_template_id(template_id, composition_mode, model, res_id)
        if model == "account.invoice":
            inv = self.env[model].browse(res_id)
            if inv.cfdi:
                xml = inv.xml_cfdi
                vals = dict(
                    name=inv.number,
                    datas=xml,
                    datas_fname='%s.xml' % (inv.number),
                    res_model='mail.compose.message',
                    res_id=0,
                    type='binary'
                )
                a = self.env['ir.attachment'].create(vals)
                rs['value']["attachment_ids"] = rs['value']["attachment_ids"] + [(4, a.id, False)]
        return rs
