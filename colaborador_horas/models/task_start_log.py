from odoo import models, fields

class TaskStartLog(models.Model):
    _name = 'task.start.log'
    _description = 'Task Start Log'

    user_id = fields.Many2one('res.users', string='User')
    start_datetime = fields.Datetime(string='Start Datetime', default=lambda self: fields.Datetime.now())
    task_id = fields.Many2one('project.task', string='Task') 
    is_timer_stopped = fields.Boolean(string='Is Timer Stopped', store=True)
    
    

    
