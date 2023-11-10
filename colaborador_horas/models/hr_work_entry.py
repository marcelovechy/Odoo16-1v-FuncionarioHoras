from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)

class MeuWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    work_entry_type = fields.Many2one('hr.work.entry.type', string='Tipos Horas')

    @api.model
    def create(self, vals):
        if 'work_entry_type_id' not in vals:
            # Verifique se o tipo de entrada de trabalho já existe com o código 'MEU_TIPO'
            work_entry_type = self.env['hr.work.entry.type'].search([('code', '=', 'my_tipo1000')], limit=1)

            if not work_entry_type:
                # Se não existir, crie o tipo de entrada de trabalho
                work_entry_type = self.env['hr.work.entry.type'].create({
                    'name': 'Meu Tipo de Entrada de Trabalho',
                    'code': 'my_tipo1000',
                })

            vals['work_entry_type_id'] = work_entry_type.id

        # Continue com a criação do registro de hr.work.entry
        record = super(MeuWorkEntry, self).create(vals)

        # Agora, chame a função update_work_entry_type
        record.update_work_entry_type()

        return record

    def update_work_entry_type(self):
        # Continua com a lógica existente para atualizar o 'work_entry_type' com base nos registros de 'hr.attendance'
        attendance_records = self.env['hr.attendance'].search([('work_entry_type', '!=', False)])

        for attendance in attendance_records:
            work_entry = self.env['hr.work.entry'].search([('x_studio_attendances_id', '=', attendance.id)])

            if work_entry:
                work_entry.write({'work_entry_type_id': attendance.work_entry_type.id})


