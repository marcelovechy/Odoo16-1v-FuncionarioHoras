{
    'name': 'Horas Colaborador',
    'version': '1.0',
    'author': 'Marcelo Simião',
    'summary': 'Gerir informações da folha salarial dos colaboradores',
    'category': 'Human Resources',
    'depends': ['base', 'hr', 'hr_payroll', 'project', 'resource', 'hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'views/colaborador_horas_views.xml',
        'views/project_task_view.xml',
        #'views/project_task_form_inherit.xml',
        #'views/templates.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
