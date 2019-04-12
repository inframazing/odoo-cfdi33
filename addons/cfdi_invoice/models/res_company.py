# -*- coding: utf-8 -*-

import re
from odoo import fields, models, api
from odoo.exceptions import Warning


class ResCompany(models.Model):
    _inherit = 'res.company'

    OPTIONS = [
        ('601', 'General de Ley Personas Morales'),
        ('603', 'Personas Morales con Fines no Lucrativos'),
        ('605', 'Sueldos y Salarios e Ingresos Asimilados a Salarios'),
        ('606', 'Arrendamiento'),
        ('608', 'Demás ingresos'),
        ('609', 'Consolidación'),
        ('610', 'Residentes en el Extranjero sin Establecimiento Permanente en México'),
        ('611', 'Ingresos por Dividendos (socios y accionistas)'),
        ('612', 'Personas Físicas con Actividades Empresariales y Profesionales'),
        ('614', 'Ingresos por intereses'),
        ('616', 'Sin obligaciones fiscales'),
        ('620', 'Sociedades Cooperativas de Producción que optan por diferir sus ingresos'),
        ('621', 'Incorporación Fiscal'),
        ('622', 'Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras'),
        ('623', 'Opcional para Grupos de Sociedades'),
        ('624', 'Coordinados'),
        ('628', 'Hidrocarburos'),
        ('607', 'Régimen de Enajenación o Adquisición de Bienes'),
        ('629', 'De los Regímenes Fiscales Preferentes y de las Empresas Multinacionales'),
        ('630', 'Enajenación de acciones en bolsa de valores'),
        ('615', 'Régimen de los ingresos por obtención de premios')]

    regimen_fiscal = fields.Selection(selection=OPTIONS, string='Régimen Fiscal')

    @api.constrains('regimen_fiscal')
    def valida_regimen_fiscal(self):
        if self.regimen_fiscal == False:
            raise Warning("La empresa %s no tiene asignado ningun Regimen Fiscal, favor de asignarlo primero" % (self.name))


    @api.constrains('vat')
    def Valida_rfc(self):
        if self.vat == False:
            raise Warning("Error de Validacion : La empresa %s no tiene ningun RFC asignado, favor de asignarlo primero" % (self.name))
        else:
            if len(self.vat) >13:
                raise Warning("El RFC %s sobrepasa los 12 caracteres para personas Fisicas y 13 para personas morales que establece el sat" % (self.vat))
            if len(self.vat) < 12:
                raise Warning("El RFC %s tiene menos de los 12 caracteres para personas Fisicas y 13 para personas morales que establece el sat" % (self.vat))
            else:
                rule = re.compile(r'^([A-ZÑ\x26]{3,4}([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|1[0-9]|2[0-9]|3[0-1]))((-)?([A-Z\d]{3}))?$')
                if not rule.search(self.vat):
                    msg = "Formato de RFC Invalido"
                    msg = msg+"El formato correcto es el siguiente:\n\n"
                    msg = msg+"-Apellido Paterno (del cual se van a utilizar las primeras 2 Letras). \n"
                    msg = msg+"-Apellido Materno (de este solo se utilizará la primera Letra).\n"
                    msg=  msg+"-Nombre(s) (sin importar si tienes uno o dos nombres, solo se utilizarà la primera Letra del primer nombre).\n"
                    msg = msg+"-Fecha de Nacimiento (día, mes y año).\n"
                    msg=  msg+"-Sexo (Masculino o Femenino).\n"
                    msg = msg+"-Entidad Federativa de nacimiento (Estado en el que fue registrado al nacer)."
                    raise Warning(msg)