from odoo import models, fields


class MeuAttendance(models.Model):
    _inherit = 'hr.attendance'

    # Adiciona um campo de seleção para tipos de horas
    work_entry_type = fields.Many2one(
        'hr.work.entry.type', string='Tipos de Horas')
