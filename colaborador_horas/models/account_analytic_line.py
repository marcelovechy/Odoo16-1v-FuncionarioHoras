from datetime import datetime, date, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    
    start_datetime_copy = fields.Datetime(string='Start Datetime Copy', default=lambda self: fields.Datetime.now())


    @api.model
    def create(self, vals):
            if 'task_id' in vals:
                task_start_log = self.env['task.start.log'].search([('task_id', '=', vals['task_id'])], order='start_datetime desc', limit=1)
                if task_start_log:
                    vals['start_datetime_copy'] = task_start_log.start_datetime

            return super(AccountAnalyticLine, self).create(vals)
    
    
    

    
    
