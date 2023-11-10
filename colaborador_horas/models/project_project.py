from datetime import datetime, date, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError, ValidationError

class ProjectProject(models.Model):
    _inherit = "project.project"
    
    def action_open_purchase_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'context': {'default_account_analytic_id': self.analytic_account_id.id},
            'target': 'self'
        }