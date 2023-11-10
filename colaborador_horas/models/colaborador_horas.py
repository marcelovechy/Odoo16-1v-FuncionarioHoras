from odoo import api, fields, models, _
from odoo.exceptions import Warning
from datetime import date, time, datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
import re
import pytz
from pytz import timezone


class ColaboradorHoras(models.Model):
    _name = "colaborador.horas"
    _description = "Gestão de horas de Funcionarios"
    
    start_datetime = fields.Datetime(string='Data de Início da Tarefa', default=lambda self: fields.Datetime.now())
    end_datetime = fields.Datetime(string='Data de Término da Tarefa')
    primeira_H_extra = fields.Float(string='Primeira Hora Extra', compute='_compute_primeira_H_extra')
    h_extras_seguindo = fields.Float(string='Horas Extras Seguintes', compute='_compute_h_extras_seguindo')
    h_extra_fims = fields.Float(string='Horas Extras de Fim de Semana', compute='_compute_h_extra_fims')
    horas_extras = fields.Float(string='Horas Extras', compute='_compute_horas_extras')
    date = fields.Date(string='Data')
    data_inicio = fields.Datetime(string='Data Inicio', default=lambda self: fields.Datetime.now())
    data_fim = fields.Datetime(string='Data Fim')
    task_id = fields.Many2one('project.task', string='Task')
    
    
    def create_attendance_records(self):
        Attendance = self.env['hr.attendance']
        WorkEntry = self.env['hr.work.entry']
        lisbon_tz = timezone('Europe/Lisbon')  
        
        # IDs para tipos de trabalho (ajuste conforme a necessidade)
        regular_work_type_id = 1  # ID do tipo de trabalho regular
        overtime_work_type_id = 9  # ID do tipo de horas extras normais
        holiday_work_type_id = 13  # ID do tipo de trabalho de feriado
        
        #IDS base de dados
        # 1	{"en_US": "Attendance"}
        # 8	{"en_US": "Out of Contract"}
        # 2	{"en_US": "Generic Time Off"}
        # 3	{"en_US": "Compensatory Time Off"}
        # 4	{"en_US": "Home Working"}
        # 5	{"en_US": "Unpaid"}
        # 6	{"en_US": "Sick Time Off"}
        # 7	{"en_US": "Paid Time Off"}
        # 9	{"en_US": "Overtime Hours"}
        # 13	{"en_US": "holiday"}
        

        records_to_create = []

        # Itera sobre as linhas de tarefa para criar registros de assistência
        for linha in self.task_lines:
            # Verifica se os dados de início, fim e colaborador estão presentes
            if linha.data_inicio and linha.data_fim and linha.colaborador:
                start_datetime = linha.data_inicio.astimezone(lisbon_tz).replace(tzinfo=None)
                end_datetime = linha.data_fim.astimezone(lisbon_tz).replace(tzinfo=None)

                # Garante que a hora de 'Check Out' não seja anterior à hora de 'Check In'
                if end_datetime <= start_datetime:
                    raise UserError("A hora de 'Check Out' não pode ser anterior à hora de 'Check In'.")

                # Define horários regulares e de pausa
                regular_start_time = start_datetime.replace(hour=8, minute=0, second=0)
                regular_end_time = start_datetime.replace(hour=17, minute=0, second=0)
                break_start_time = start_datetime.replace(hour=12, minute=0, second=0)
                break_end_time = start_datetime.replace(hour=13, minute=0, second=0)

                # Inicializa variáveis para rastrear as horas trabalhadas
                regular_hours = 0.0
                first_overtime_hour = 0.0
                additional_overtime_hours = 0.0

                current_time = start_datetime

                # Calcula as horas trabalhadas e as horas extras
                while current_time < end_datetime:
                    next_time = min(current_time + timedelta(hours=1), end_datetime)
                    if current_time < regular_start_time:
                        pass
                    elif current_time < break_start_time:
                        if next_time <= break_start_time:
                            regular_hours += (next_time - current_time).total_seconds() / 3600.0
                        else:
                            regular_hours += (break_start_time - current_time).total_seconds() / 3600.0
                            if next_time <= break_end_time:
                                first_overtime_hour += (next_time - break_start_time).total_seconds() / 3600.0
                            else:
                                first_overtime_hour += (break_end_time - break_start_time).total_seconds() / 3600.0
                    else:
                        additional_overtime_hours += (next_time - current_time).total_seconds() / 3600.0

                    current_time = next_time

                # Procura o funcionário com base no nome fornecido na linha
                employee = self.env['hr.employee'].search([('name', '=', linha.colaborador)], limit=1)

                if employee:
                    # Verifique se já existe um registro de assistência para o funcionário neste período
                    existing_attendance = Attendance.search([
                        ('employee_id', '=', employee.id),
                        ('check_in', '<=', start_datetime.strftime('%Y-%m-%d %H:%M:%S')),
                        ('check_out', '>=', end_datetime.strftime('%Y-%m-%d %H:%M:%S'))
                    ])

                    if not existing_attendance:
                        # O funcionário não tem registro de assistência durante este período,
                        # então podemos criar um novo registro.
                        if regular_hours > 0:
                            check_out = min(end_datetime, regular_end_time).strftime('%Y-%m-%d %H:%M:%S')
                            Attendance.create({
                                'employee_id': employee.id,
                                'check_in': start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                                'check_out': check_out,
                                'work_entry_type': regular_work_type_id #usando ID válido de Attendance
                            })

                        if first_overtime_hour > 0:
                            first_overtime_end = regular_end_time + timedelta(hours=1)
                            check_in_overtime = regular_end_time
                            check_out_overtime = min(end_datetime, first_overtime_end)
                            check_in_overtime_str = check_in_overtime.strftime('%Y-%m-%d %H:%M:%S')
                            check_out_overtime_str = check_out_overtime.strftime('%Y-%m-%d %H:%M:%S')
                            Attendance.create({
                                'employee_id': employee.id,
                                'check_in': check_in_overtime_str,
                                'check_out': check_out_overtime_str,
                                'work_entry_type': overtime_work_type_id # usando ID válido de Overtime hours
                            })

                        if additional_overtime_hours > 0:
                            check_in_overtime = regular_end_time + timedelta(hours=1)
                            check_out_overtime = min(end_datetime, regular_end_time + timedelta(hours=1) + timedelta(hours=additional_overtime_hours))
                            check_in_overtime_str = check_in_overtime.strftime('%Y-%m-%d %H:%M:%S')
                            check_out_overtime_str = check_out_overtime.strftime('%Y-%m-%d %H:%M:%S')
                            Attendance.create({
                                'employee_id': employee.id,
                                'check_in': check_in_overtime_str,
                                'check_out': check_out_overtime_str,
                                'work_entry_type': holiday_work_type_id  # usando ID válido de holiday
                            })
                            
    #func p criar as horas de entrada no trabalho em horas extras
    def generate_work_entries(self):
        # Crie uma instância do modelo 'hr.work.entry' para criar entradas de trabalho
        WorkEntry = self.env['hr.work.entry']

        # Defina o fuso horário de Lisboa
        lisbon_tz = pytz.timezone('Europe/Lisbon')

        for linha in self.task_lines:
            # Verifique se a linha possui uma data de início e horas extras maiores que 0
            if linha.data_inicio and linha.primeira_H_extra > 0:
                # Defina a hora de início para a primeira hora extra (17:01)
                start_datetime = linha.data_inicio.replace(hour=17, minute=1, tzinfo=lisbon_tz)
                primeira_H_extra = linha.primeira_H_extra

                # Converta a hora de início para um objeto de data e hora "naive"
                start_datetime = start_datetime.replace(tzinfo=None)

                # Crie uma entrada de trabalho para a primeira hora extra
                WorkEntry.create({
                    'employee_id': 3,  # Substitua pelo ID do colaborador apropriado
                    'date_start': start_datetime,
                    'date_stop': start_datetime + timedelta(hours=1),
                    'name': 'Primeira Hora Extra',
                    'duration': min(primeira_H_extra, 1),
                    'work_entry_type_id': 11,  # Substitua pelo ID do tipo de entrada apropriado
                    'state': 'draft',
                    'conflict': False
                })

                # linha.h_extras_seguindo é uma variável que contém o numero de horas extras seguintes, ou seja que excedem a primeira hora extra e saõ alocadas em dias subsequentes.
                # Calculate the remaining overtime hours
                remaining_hours = max(linha.overtime_hours - 1, 0)

                while remaining_hours > 0:
                    # Calcule as horas de início e término para o próximo dia
                    next_day_start = start_datetime.replace(hour=18, minute=1, second=00)
                    next_day_end = next_day_start.replace(hour=23, minute=59, second=59)

                    # Calcule a duração até o final do dia atual
                    duration_until_end_of_day = (next_day_end - next_day_start).total_seconds() / 3600

                    # Determine quantas horas podem ser alocadas no dia atual
                    block_duration = min(duration_until_end_of_day, remaining_hours)

                    # Crie uma entrada de trabalho para o bloco de horas extras no primeiro dia
                    WorkEntry.create({
                        'employee_id': 3,  
                        'date_start': start_datetime,
                        'date_stop': start_datetime + timedelta(hours=block_duration),
                        'name': 'Horas Extras Seguintes',
                        'duration': block_duration,
                        'work_entry_type_id': 9,  
                        'state': 'draft',
                        'conflict': False
                    })

                    # Atualize as horas extras restantes
                    remaining_hours -= block_duration

                    if remaining_hours > 0:
                        # Calcule as horas de início e término para o segundo dia
                        second_day_end = start_datetime.replace(hour=7, minute=59, second=59) + timedelta(days=1)
                        block_duration = min(remaining_hours, (second_day_end - start_datetime).total_seconds() / 3600)

                        # Crie uma entrada de trabalho para o bloco de horas extras no segundo dia
                        WorkEntry.create({
                            'employee_id': 3,  # Substitua pelo ID do colaborador apropriado
                            'date_start': start_datetime.replace(hour=0, minute=0, second=0) + timedelta(days=1),
                            'date_stop': start_datetime.replace(hour=7, minute=59, second=59) + timedelta(days=1),
                            'name': 'Horas Extras Seguintes (2º Bloco)',
                            'duration': block_duration,
                            'work_entry_type_id': 9,  # Substitua pelo ID do tipo de entrada apropriado
                            'state': 'draft',
                            'conflict': False
                        })

                        # Atualize as horas extras restantes
                        remaining_hours -= block_duration
                    # Avance para o próximo dia
                    start_datetime = next_day_start
                    
    @api.depends()
    def _compute_create_attendance_records(self):
        for record in self:
            record.action_create_attendance_records = True

    
    @api.depends('horas_extras', 'data_inicio', 'data_fim')
    def _compute_primeira_H_extra(self):
        for linha in self:
            if linha.horas_extras > 0:
                linha.primeira_H_extra = 1.0
            else:
                linha.primeira_H_extra = 0.0

    @api.depends('horas_extras', 'data_inicio', 'data_fim')
    def _compute_h_extras_seguindo(self):
        for linha in self:
            if linha.horas_extras > 1:
                linha.h_extras_seguindo = linha.horas_extras - 1
            else:
                linha.h_extras_seguindo = 0.0

    @api.depends('horas_extras', 'data_inicio', 'data_fim')
    def _compute_h_extra_fims(self):
        for linha in self:
            if linha.horas_extras > 0 and linha.data_inicio and linha.data_fim:
                # Check if either data_inicio or data_fim falls on a weekend (Saturday or Sunday)
                if linha.data_inicio.weekday() >= 5 or linha.data_fim.weekday() >= 5:
                    linha.h_extra_fims = linha.horas_extras
                else:
                    linha.h_extra_fims = 0.0
            else:
                linha.h_extra_fims = 0.0

    def _compute_horas_extras(self):
        for linha in self:
            if linha.data_fim and linha.data_inicio:
                # Calculate the difference in hours between data_fim and data_inicio
                horas_worked = (linha.data_fim - linha.data_inicio).total_seconds() / 3600.0
    
                # Calculate the total hours worked overtime (if more than 8 hours)
                horas_extras = max(horas_worked - 8, 0)
    
                linha.horas_extras = horas_extras
            else:
                linha.horas_extras = 0.0
                    

    month = fields.Selection([
        ('01', 'Janeiro'), ('02', 'Fevereiro'), ('03', 'Março'), ('04', 'Abril'),
        ('05', 'Maio'), ('06', 'Junho'), ('07', 'Julho'), ('08', 'Agosto'),
        ('09', 'Setembro'), ('10', 'Outubro'), ('11', 'Novembro'), ('12', 'Dezembro'),
    ], string='Mês', required=True, default='01')
    
    year = fields.Char(string='Ano', required=True, default=str(datetime.now().year))
    
    # Restrição para garantir que o ano seja maior que 0
    @api.constrains('year')
    def _check_year(self):
        for record in self:
            if not record.year.isdigit() or int(record.year) <= 0:
                raise ValidationError("O ano deve ser um número inteiro maior que 0.")
            
    @api.model
    def _default_year(self):
        current_year = fields.Date.today().year
        return str(current_year)  # Convertemos para string

    
    projeto_ids = fields.Many2many('project.task', string='Tarefas do Projeto')
    date = fields.Date(string='Data')
    date_last_updated = fields.Datetime(string='Data de Atualização', readonly=True)
    active = fields.Boolean(string='Ativo', default=True)


    #Sempre que um registro for criado ou atualizado, atualize o campo date_last_updated com a data e hora atuais.
    @api.model
    def create(self, vals):
        vals['date_last_updated'] = fields.Datetime.now()
        return super(ColaboradorHoras, self).create(vals)

    def write(self, vals):
        vals['date_last_updated'] = fields.Datetime.now()
        return super(ColaboradorHoras, self).write(vals)

    
    def action_colaborador(self):
        return {
            'name': 'Gestão de Horas de Funcionários',
            'view_mode': 'form',
            'res_model': 'colaborador.horas',
            'view_id': self.env.ref('colaborador_horas.view_colaborador_horas_form').id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
        
    task_lines = fields.One2many('colaborador.horas.tarefa.linha', 'colaborador_horas_id', string='Linhas de Horas de Tarefas')

    # busca e exibe as horas registradas em tarefas para o mês e ano especificados, utilizando o modelo "project.task" e "account.analytic.line", para realizar busca e preencher o campo task_lines com os resultados.
    def ver_horas_tarefas(self):
        start_time = datetime.strptime('08:00', '%H:%M').time()
        end_time = datetime.strptime('17:00', '%H:%M').time()
        # Exibir as horas das tarefas
        task_model = self.env['project.task']
        task_line_model = self.env['account.analytic.line']

         # Identificar o mês e ano da consulta atual
        selected_month = int(self.month)
        selected_year = int(self.year)

        # Filtre os registros antigos do mesmo mês e ano
        old_records = self.search([
            ('month', '=', selected_month),
            ('year', '=', selected_year),
            ('id', '!=', self.id),  # Exclua o registro atual da busca
        ])

        # Oculte os registros antigos definindo o campo 'active' como False
        old_records.write({'active': False})

        # Atualize a data de atualização do registro atual
        self.write({'date_last_updated': fields.Datetime.now()})
                
        # Calcule o primeiro e o último dia do mês selecionado
        first_day_of_month = datetime(int(self.year), int(self.month), 1)
        last_day_of_month = (first_day_of_month + relativedelta(months=1)) - timedelta(days=1)
        #_logger.info(f"First Day: {first_day_of_month}, Last Day: {last_day_of_month}")
        
        horas_extras =0.0
        task_line_records = [] # Lista para armazenar os registros de linhas de tarefa

        for task in task_model.search([]):
            for line in task.timesheet_ids:
                total_hours_worked = 0.0

                start_datetime_copy = fields.Datetime.from_string(line.start_datetime_copy)
                create_date = fields.Datetime.from_string(line.create_date)
                

                # Verifique se start_datetime_copy não é None antes de subtrair
                if start_datetime_copy:
                

                    start_datetime = max(start_datetime_copy, create_date - timedelta(hours=start_time.hour))
                    end_datetime = min(create_date, start_datetime_copy.replace(hour=end_time.hour, minute=0, second=0))

                    if start_datetime < end_datetime:
                        # Calcule as horas trabalhadas no dia
                        working_hours = (end_datetime - start_datetime).total_seconds() / 3600.0  # Converter segundos em horas
                        # Subtrair o intervalo de almoço (1 hora) se o dia tiver mais de 4 horas trabalhadas
                        if working_hours > 4:
                            working_hours -= 1

                        total_hours_worked += working_hours
                        #overtime_hours = max(0, total_hours_worked - working_hours)  # Horas extras

                    # Verifique se a tarefa abrange vários dias
                    while start_datetime_copy.date() != create_date.date():
                        
                        next_day_start = start_datetime_copy.replace(hour=start_time.hour, minute=0, second=0)
                        next_day_end = start_datetime_copy.replace(hour=end_time.hour, minute=0, second=0)

                        if next_day_start < next_day_end:
                            total_hours_worked += (next_day_end - next_day_start).total_seconds() / 3600.0
                        

                        # Avance para o próximo dia
                        start_datetime_copy = next_day_start + timedelta(days=1)

                    # Verifique se a data da linha está dentro do mês selecionado
                    line_date = fields.Datetime.from_string(line.date)
                    if first_day_of_month <= line_date <= last_day_of_month:
                     
                        # Crie um registro para a linha atual
                        task_line_records.append((0, 0, {
                            #'colaborador_horas_id': self.id,
                            #'task_id': task.id,
                            'task_name': task.name,
                            'hours_logged': line.unit_amount,
                            #'horas_extras': line.horas_extras,
                            'total_hours_worked': total_hours_worked,
                            'colaborador': line.employee_id.name,
                            'date': line.date,
                            'data_inicio': line.start_datetime_copy,
                            #'data_inicio': line.datetime.now(),
                            'data_fim': create_date                            
                        }))
                    
        self.task_lines = task_line_records   
        
    @api.model
    def create(self, vals_list):
        # Verifique se a entrada é uma lista de dicionários
        if isinstance(vals_list, list) and all(isinstance(vals, dict) for vals in vals_list):
            # Processar operações em lote
            new_records = []
            for vals in vals_list:
                new_record = super(ColaboradorHoras, self).create(vals)
                new_records.append(new_record)
            return new_records
        else:
            # Operação de criação individual
            return super(ColaboradorHoras, self).create(vals_list)
               
#classe criada com os campos necessário para armazenar informações relacionadas às tarefas e horas registradas.
class ColaboradorHorasTarefaLinha(models.Model):
    _name = 'colaborador.horas.tarefa.linha'
    _description = 'Linhas de Horas de Tarefas'

    colaborador_horas_id = fields.Many2one('colaborador.horas', string='Funcionario Horas')
    task_name = fields.Char(string='Nome da Tarefa')
    hours_logged = fields.Float(string='Horas Registradas')
    total_hours_worked = fields.Float(string='Horas de Trabalho Regulares')
    colaborador = fields.Char(string='Nome do Funcionario')
    date = fields.Date(string='Data')
    data_inicio = fields.Datetime(string='Inicio', default=lambda self: fields.Datetime.now())
    data_fim = fields.Datetime(string='Fim')
    #task_id = fields.Many2one('project.task', string='Task')
    primeira_H_extra = fields.Float(string='Primeira Hora Extra', compute='_compute_primeira_H_extra')
    h_extras_seguindo = fields.Float(string='Horas Extras Seguintes', compute='_compute_h_extras_seguindo')
    h_extra_fims = fields.Float(string='Horas Extras de Fim de Semana', compute='_compute_h_extra_fims')
    horas_extras = fields.Float(string='Horas Extras', compute='_compute_horas_extras')
    
    date_last_updated = fields.Datetime(string='Data de Atualização', readonly=True)
    active = fields.Boolean(string='Ativo', default=True)

    @api.depends('horas_extras', 'data_inicio', 'data_fim')
    def _compute_primeira_H_extra(self):
        for linha in self:
            if linha.horas_extras > 0:
                linha.primeira_H_extra = 1.0
            else:
                linha.primeira_H_extra = 0.0

    @api.depends('horas_extras', 'data_inicio', 'data_fim')
    def _compute_h_extras_seguindo(self):
        for linha in self:
            if linha.horas_extras > 1:
                linha.h_extras_seguindo = linha.horas_extras - 1
            else:
                linha.h_extras_seguindo = 0.0

    @api.depends('horas_extras', 'data_inicio', 'data_fim')
    def _compute_h_extra_fims(self):
        for linha in self:
            if linha.horas_extras > 0 and linha.data_inicio and linha.data_fim:
                # Check if either data_inicio or data_fim falls on a weekend (Saturday or Sunday)
                if linha.data_inicio.weekday() >= 5 or linha.data_fim.weekday() >= 5:
                    linha.h_extra_fims = linha.horas_extras
                else:
                    linha.h_extra_fims = 0.0
            else:
                linha.h_extra_fims = 0.0

    def _compute_horas_extras(self):
        for linha in self:
            if linha.data_fim and linha.data_inicio:
                # Calculate the difference in hours between data_fim and data_inicio
                horas_worked = (linha.data_fim - linha.data_inicio).total_seconds() / 3600.0
    
                # Calculate the total hours worked overtime (if more than 8 hours)
                horas_extras = max(horas_worked - 8, 0)
    
                linha.horas_extras = horas_extras
            else:
                linha.horas_extras = 0.0

    
    # Função para verificar a unicidade dos IDs de tarefa e atualizar ou criar a linha
    def _check_task_id_unique(self):
        for linha in self:
            if linha.task_id:
                # Verificar se já existe outra linha com o mesmo task_id
                existing_line = self.search([
                    ('task_id', '=', linha.task_id),
                    ('id', '!=', linha.id)  # Excluir a linha atual da busca
                ])
                if existing_line:
                    # Se houver uma linha existente, exibir uma mensagem de confirmação
                    message = _("Uma linha com o mesmo ID de tarefa já existe. Deseja atualizar a linha existente?")
                    # Exibir uma mensagem de confirmação ao usuário
                    warning = {
                        'title': _('Atenção!'),
                        'message': message,
                    }
                    return {'warning': warning}
                else:
                    pass
