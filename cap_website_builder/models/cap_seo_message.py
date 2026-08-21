from odoo import fields, models


class CapSeoMessage(models.Model):
    _name = 'cap.seo.message'
    _description = 'SEO Conversation Message'
    _order = 'id'

    query_id = fields.Many2one(
        'cap.seo.query', string='Conversation', required=True,
        ondelete='cascade', index=True)
    role = fields.Selection(
        [('user', 'User'), ('assistant', 'Assistant'), ('error', 'Error')],
        string='Role', required=True)
    body = fields.Html(string='Body', sanitize=False)

    # Filled on assistant messages, so an answer can be checked against the
    # query that actually produced it.
    plan_json = fields.Text(string='Query Sent', readonly=True)
    result_json = fields.Text(string='Rows Returned', readonly=True)
    row_count = fields.Integer(string='Rows', readonly=True)
    source = fields.Char(string='Source', readonly=True)

    def _to_dict(self):
        """Shape a message for the chat client."""
        return [{
            'id': message.id,
            'role': message.role,
            'body': message.body or '',
            'plan_json': message.plan_json or '',
            'row_count': message.row_count,
            'source': message.source or '',
        } for message in self]
