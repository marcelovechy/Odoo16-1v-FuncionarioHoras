from odoo import models, fields


class ProjectTask(models.Model):
    _inherit = 'project.task'
    
    
    start_log_ids = fields.One2many('task.start.log', 'task_id', string='Start Logs', store=True) #task_id relaciona o modelo task.start.log de volta ao modelo project.task
    start_timer_datetime = fields.Datetime(string='Start Timer Datetime', store=True, readonly=True)
    
    
    def action_timer_stop(self):
        for task in self:
            # Filtrar os registros de log de início que não foram interrompidos
            start_logs = task.start_log_ids.filtered(lambda log: not log.is_timer_stopped)
            start_logs.write({
                'is_timer_stopped': True,
                'start_datetime_copy': start_logs.mapped('start_datetime'),
            })


    def action_start_task(self):
        for task in self:
            start_log_vals = {
                'user_id': self.env.user.id,
                'start_datetime': fields.Datetime.now(),
                'task_id': task.id,
            }
            start_log = self.env['task.start.log'].create(start_log_vals)
            # Adicione o registro criado ao campo one2many start_log_ids da tarefa
            task.start_log_ids = [(4, start_log.id)]
            
        self.action_timer_start()

    
    
    

    # def action_timer_stop(self):
    #     for task in self:
    #         # Filtrar os registros de log de início que não foram interrompidos
    #         start_logs = task.start_log_ids.filtered(lambda log: not log.is_timer_stopped)

    #         # Atualizar cada registro de log
    #         for start_log in start_logs:
    #             # Supondo que 'account_analytic_line_id' seja o campo de relação entre 'task.start.log' e 'account.analytic.line'
    #             if start_log.account_analytic_line_id:
    #                 start_log.account_analytic_line_id.write({
    #                     'start_datetime_copy': start_log.start_datetime,
    #                 })

    #             # Marcar o registro de log como interrompido
    #             start_log.write({
    #                 'is_timer_stopped': True,
    #             })

    
    # def action_start_task(self):
    #     # Itera sobre cada registro de tarefa (self representa a tarefa atual)
    #     for task in self:
    #         # Cria um dicionário com os valores para o registro de início
    #         start_log_vals = {
    #             'user_id': self.env.user.id,  # ID do usuário atual
    #             'start_datetime': fields.Datetime.now(),  # Data/hora atual
    #             'task_id': task.id,  # ID da tarefa
    #         }

    #         # Cria um registro no modelo 'task.start.log' usando os valores definidos
    #         start_log = self.env['task.start.log'].create(start_log_vals)

    #         # Adiciona o registro de log recém-criado ao campo one2many 'start_log_ids' da tarefa
    #         task.start_log_ids = [(4, start_log.id)]

    #     # Chama a função 'action_timer_start' para iniciar um temporizador associado à tarefa
    #     self.action_timer_start()


