import json

from dateutil.relativedelta import relativedelta
from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.translate import _

from . import google_client
from .ai_provider import AIProviderError, get_provider
from .google_client import GoogleClientError


# Search Console data lags a couple of days; asking for yesterday returns
# nothing and reads as a bug.
GSC_LAG_DAYS = 3
DEFAULT_WINDOW_DAYS = 28
# How many earlier turns are replayed to the planner.
HISTORY_TURNS = 6

PLANNER_PROMPT = """You turn a question about website traffic into a single \
JSON query.

Answer with JSON only. No explanation, no markdown code fences.

Shape:
{
  "source": "search_console" | "analytics" | "both",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "dimensions": [...],
  "metrics": [...],
  "filters": [{"dimension": "...", "operator": "contains|equals|notContains|notEquals", "expression": "..."}],
  "limit": 100,
  "order_by": "metric name"
}

Rules:
- Use search_console for anything about Google search itself: queries people
  typed, impressions, clicks from search, average position, CTR.
- Use analytics for on-site behaviour: sessions, users, page views, channels,
  engagement, revenue.
- Use both only when the question genuinely needs the two together.
- Pick dimensions and metrics only from the lists below. Never invent names.
- Stay inside the date range given below unless the question names another
  period; never ask for dates in the future.
- filters and order_by are optional. Omit them rather than guessing.

Choosing dimensions - this is where these queries usually go wrong:
- Use ONE dimension unless the question truly needs a breakdown. The row limit
  applies to the combination of dimensions, so asking for query + date spends
  the whole limit on a handful of terms repeated once per day, and everything
  else falls outside the results.
- "which queries / what do people search for / which topics / which pages" ->
  dimensions ["query"] or ["page"], no date.
- "trend / over time / rising / falling / compared with last month" ->
  dimensions ["date"] alone, or ["query"] with a filter naming the topic.

Choosing the limit:
- Results are returned best-first (most clicks), so a small limit shows only
  your best-known terms - usually your own brand name.
- Exploratory questions ("what are people searching", "which topics", "what
  should we write about") need limit 200 or more, or the answer is just the
  brand.
- Use a small limit only when the question asks for a top N.

Filtering:
- When the question is about a subject rather than the whole site, filter for
  it: {"dimension": "query", "operator": "contains", "expression": "erp"}.
- To see demand beyond the company's own name, exclude the brand:
  {"dimension": "query", "operator": "notContains", "expression": "<brand>"}.
  Infer the brand from the site address given below.

What Search Console can and cannot tell you:
- It reports only searches where THIS site already appeared in Google. It is
  not keyword research and knows nothing about the wider market, competitors,
  or search volumes the site does not rank for.
- So "what are the trends in <industry>" can only be answered as "here is the
  demand this site is already visible for". Plan the closest query you can and
  let the answering step explain the limit.

Earlier turns of this conversation are given as context. A follow-up such as
"now exclude the brand" or "same thing for India" refers to the previous
query: start from it and change only what the follow-up asks for.

When the message is not a data question at all - a greeting, a thank you, or a
question about what you can do - do not invent a query. Answer with this
instead:

{"reply": "<one or two sentences, and an example of something they could ask>"}
"""

ANSWER_PROMPT = """You explain website traffic data to a marketing colleague.

You are given a question and the rows that answer it. Rules:
- Answer the question directly in the first sentence.
- Quote the actual numbers from the rows. Never invent a figure, never round
  away a difference that matters.
- Point out anything genuinely notable in the data, briefly.
- Plain HTML only: <p>, <ul>, <li>, <strong>, <table>. No markdown, no code
  fences, no <script>.

Know what you are looking at:
- Search Console rows are only the searches where this site already appeared in
  Google. They are not market research: they say nothing about competitors, or
  about demand the site does not yet rank for.
- Branded searches (the company's own name) usually dominate. Say so when they
  do, and answer from the non-branded rows, which are the ones that show real
  subject demand.

When the rows do not fully answer the question:
- Do not reply that the data does not answer it and stop. That is not useful.
- Answer the nearest question the rows DO settle, label it as such, and say in
  one line what would be needed for the original question - a different query,
  a wider limit, or a tool other than Search Console.
"""


def _default_date_to(self):
    return fields.Date.today() - relativedelta(days=GSC_LAG_DAYS)


def _default_date_from(self):
    return _default_date_to(self) - relativedelta(days=DEFAULT_WINDOW_DAYS)


def _default_ai_model(self):
    return self.env['cap.ai.model']._get_default_model()


class CapSeoQuery(models.Model):
    _name = 'cap.seo.query'
    _description = 'SEO Conversation'
    _order = 'last_activity desc, id desc'

    name = fields.Char(
        string='Title', required=True, default=lambda self: _('New chat'))
    ai_model_id = fields.Many2one(
        'cap.ai.model', string='AI Model', required=True,
        default=_default_ai_model, ondelete='restrict')

    date_from = fields.Date(string='From', default=_default_date_from)
    date_to = fields.Date(string='To', default=_default_date_to)

    message_ids = fields.One2many(
        'cap.seo.message', 'query_id', string='Messages')
    message_count = fields.Integer(
        string='Messages', compute='_compute_message_count')
    last_activity = fields.Datetime(
        string='Last Activity', default=fields.Datetime.now, index=True)

    @api.depends('message_ids')
    def _compute_message_count(self):
        data = self.env['cap.seo.message']._read_group(
            [('query_id', 'in', self.ids)], groupby=['query_id'],
            aggregates=['__count'])
        counts = {query.id: count for query, count in data}
        for record in self:
            record.message_count = counts.get(record.id, 0)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _check_seo_group(self):
        if not self.env.user.has_group('website.group_website_designer'):
            raise AccessError(_(
                "You need Website Designer access rights to query Google."))

    def _planner_prompt(self):
        return PLANNER_PROMPT + (
            "\nSearch Console dimensions: %s"
            "\nSearch Console metrics (always all four): %s"
            "\nAnalytics dimensions: %s"
            "\nAnalytics metrics: %s\n" % (
                ', '.join(google_client.GSC_DIMENSIONS),
                ', '.join(google_client.GSC_METRICS),
                ', '.join(google_client.GA4_DIMENSIONS),
                ', '.join(google_client.GA4_METRICS),
            ))

    def _planner_messages(self, question):
        """Replay recent turns so follow-ups resolve against the last query."""
        sources = google_client.available_sources(self.env)
        configured = [name for name, available in sources.items() if available]
        messages = []
        history = self.message_ids.filtered(
            lambda message: message.role in ('user', 'assistant'))
        for message in history[-HISTORY_TURNS:]:
            if message.role == 'user':
                messages.append({'role': 'user', 'content': message.body or ''})
            elif message.plan_json:
                messages.append({
                    'role': 'assistant',
                    'content': 'Query used:\n%s' % message.plan_json,
                })
        messages.append({'role': 'user', 'content': (
            "Today is %(today)s.\n"
            "Default date range: %(start)s to %(end)s.\n"
            "Sources configured: %(sources)s.\n"
            "Site: %(site)s\n\n"
            "Question: %(question)s" % {
                'today': fields.Date.today(),
                'start': self.date_from,
                'end': self.date_to,
                'sources': ', '.join(configured) or 'none',
                'site': google_client.google_config(
                    self.env)['gsc_site_url'] or _('(not set)'),
                'question': question,
            })})
        return messages

    def _clamp_dates(self, spec):
        """Keep the AI's dates inside the range the user asked for."""
        spec['start_date'] = max(str(spec['start_date']), str(self.date_from))
        spec['end_date'] = min(str(spec['end_date']), str(self.date_to))
        if spec['start_date'] > spec['end_date']:
            spec['start_date'], spec['end_date'] = (
                str(self.date_from), str(self.date_to))
        return spec

    def _run_spec(self, client, spec):
        results = {}
        for source in google_client._sources(spec.get('source')):
            if source == google_client.SOURCE_SEARCH_CONSOLE:
                results[source] = client.search_console(spec)
            else:
                results[source] = client.analytics(spec)
        return results

    def _post(self, role, body, **values):
        self.last_activity = fields.Datetime.now()
        return self.env['cap.seo.message'].create(dict({
            'query_id': self.id,
            'role': role,
            'body': body,
        }, **values))

    def _error(self, error):
        return self._post('error', Markup('<p>%s</p>') % str(error))

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------
    def action_send_message(self, text):
        """Answer one turn. Returns the new messages for the chat client."""
        self.ensure_one()
        self._check_seo_group()
        text = (text or '').strip()
        if not text:
            raise UserError(_("Write a question first."))

        posted = self._post('user', Markup('<p>%s</p>') % escape(text))
        if self.name == _('New chat'):
            self.name = text[:60]

        try:
            provider = get_provider(self.ai_model_id)
            client = google_client.get_client(self.env)
        except (AIProviderError, GoogleClientError) as error:
            return (posted + self._error(error))._to_dict()

        try:
            raw_plan = provider.chat(
                self._planner_prompt(), self._planner_messages(text))
        except AIProviderError as error:
            return (posted + self._error(error))._to_dict()

        spec = _extract_json(raw_plan)
        if spec is None:
            return (posted + self._error(_(
                "The AI did not return a usable query. Try rephrasing the "
                "question."
            )))._to_dict()

        # Greetings and "what can you do" questions get a plain reply rather
        # than a query nobody asked for.
        if spec.get('reply') and not spec.get('source'):
            reply = self._post(
                'assistant', Markup('<p>%s</p>') % escape(spec['reply']))
            return (posted + reply)._to_dict()

        try:
            spec = google_client.validate_spec(
                spec, google_client.available_sources(self.env))
            spec = self._clamp_dates(spec)
            results = self._run_spec(client, spec)
        except GoogleClientError as error:
            return (posted + self._error(error))._to_dict()

        plan_json = json.dumps(spec, indent=2, default=str)
        row_count = sum(len(rows) for rows in results.values())
        limit = self.ai_model_id.sudo().max_context_chars or 60000
        tables = '\n\n'.join(
            '=== %s ===\n%s' % (
                source, google_client.rows_to_table(rows, limit // 2))
            for source, rows in results.items())

        try:
            answer = provider.chat(ANSWER_PROMPT, [{
                'role': 'user',
                'content': 'Question: %s\n\nQuery run:\n%s\n\nRows:\n%s' % (
                    text, plan_json, tables),
            }])
        except AIProviderError as error:
            return (posted + self._error(error))._to_dict()

        assistant = self._post(
            'assistant', answer,
            plan_json=plan_json,
            result_json=json.dumps(results, indent=2, default=str),
            row_count=row_count,
            source=', '.join(results.keys()),
        )
        return (posted + assistant)._to_dict()

    @api.model
    def action_open_chat(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'cap_seo_chat',
            'name': _('SEO Insights'),
        }

    def load_chat(self):
        """Everything the client needs to render one conversation."""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            # Plain strings: the date inputs in the composer header expect
            # YYYY-MM-DD, not whatever the serializer makes of a date object.
            'date_from': fields.Date.to_string(self.date_from) or '',
            'date_to': fields.Date.to_string(self.date_to) or '',
            'ai_model_id': self.ai_model_id.id,
            'messages': self.message_ids._to_dict(),
        }


def _extract_json(answer):
    """Pull the JSON object out of a model answer."""
    if not answer:
        return None
    text = answer.strip()
    if '```' in text:
        parts = text.split('```')
        text = max(parts, key=len)
        if text.lstrip().startswith('json'):
            text = text.lstrip()[4:]
    start, end = text.find('{'), text.rfind('}')
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except ValueError:
        return None
