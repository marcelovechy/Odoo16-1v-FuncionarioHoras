from odoo import models, fields

class MeuModeloPayroll(models.Model):
    
    _inherit = 'resource.calendar.attendance'

    horas_regulares = fields.Float(string='Horas Regulares')
    horas_extras = fields.Float(string='Horas Extras')
