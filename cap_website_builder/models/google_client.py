"""Read-only access to Google Search Console and Google Analytics 4.

Service-account authentication done by hand: PyJWT signs the assertion,
requests exchanges it for an access token. That keeps the module free of the
google-api-python-client dependency, which is not installed here.
"""
import json
import time
import urllib.parse

import jwt
import requests

from odoo.tools.translate import _


TOKEN_URI = 'https://oauth2.googleapis.com/token'
JWT_GRANT = 'urn:ietf:params:oauth:grant-type:jwt-bearer'
SCOPES = ' '.join((
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/analytics.readonly',
))
GSC_ENDPOINT = ('https://searchconsole.googleapis.com/webmasters/v3/sites/'
                '%s/searchAnalytics/query')
GA4_ENDPOINT = 'https://analyticsdata.googleapis.com/v1beta/%s:runReport'

DEFAULT_TIMEOUT = 60
MAX_ROWS = 250
DEFAULT_ROWS = 100

SOURCE_SEARCH_CONSOLE = 'search_console'
SOURCE_ANALYTICS = 'analytics'

# Everything a generated query spec is allowed to ask for. Anything outside
# these lists is refused before a request is sent.
GSC_DIMENSIONS = (
    'query', 'page', 'country', 'device', 'searchAppearance', 'date')
GSC_METRICS = ('clicks', 'impressions', 'ctr', 'position')
GA4_DIMENSIONS = (
    'date', 'pagePath', 'pageTitle', 'sessionSource', 'sessionMedium',
    'sessionDefaultChannelGroup', 'country', 'deviceCategory', 'landingPage')
GA4_METRICS = (
    'activeUsers', 'sessions', 'screenPageViews', 'engagedSessions',
    'engagementRate', 'averageSessionDuration', 'bounceRate', 'newUsers',
    'conversions', 'totalRevenue')
FILTER_OPERATORS = ('contains', 'equals', 'notContains', 'notEquals')

# GA4 speaks a different filter dialect than Search Console.
GA4_MATCH_TYPES = {
    'contains': ('CONTAINS', False),
    'equals': ('EXACT', False),
    'notContains': ('CONTAINS', True),
    'notEquals': ('EXACT', True),
}


class GoogleClientError(Exception):
    """Anything that stopped us getting data out of Google."""


class GoogleClient:
    """One configured service account, talking to one site and/or property."""

    def __init__(self, service_account_json, gsc_site_url=None,
                 ga4_property_id=None, timeout=DEFAULT_TIMEOUT):
        try:
            key = json.loads(service_account_json or '{}')
        except ValueError:
            raise GoogleClientError(
                _("The service account key is not valid JSON. Paste the whole "
                  "key file, including the outer braces."))
        self.client_email = key.get('client_email')
        self.private_key = key.get('private_key')
        self.token_uri = key.get('token_uri') or TOKEN_URI
        if not self.client_email or not self.private_key:
            raise GoogleClientError(
                _("The service account key is missing 'client_email' or "
                  "'private_key'. Use the JSON key of a service account, not "
                  "an OAuth client secret."))

        self.gsc_site_url = (gsc_site_url or '').strip()
        self.ga4_property_id = _normalise_property(ga4_property_id)
        self.timeout = timeout or DEFAULT_TIMEOUT
        self._token = None
        self._token_expires_at = 0

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    def _access_token(self):
        now = int(time.time())
        if self._token and now < self._token_expires_at:
            return self._token

        assertion = jwt.encode(
            {
                'iss': self.client_email,
                'scope': SCOPES,
                'aud': self.token_uri,
                'iat': now,
                'exp': now + 3600,
            },
            self.private_key,
            algorithm='RS256',
        )
        try:
            response = requests.post(
                self.token_uri,
                data={'grant_type': JWT_GRANT, 'assertion': assertion},
                timeout=self.timeout,
            )
        except requests.exceptions.RequestException as error:
            raise GoogleClientError(_("Could not reach Google: %s", error))

        if response.status_code != 200:
            raise GoogleClientError(_(
                "Google refused the service account key (HTTP %(code)s): "
                "%(body)s",
                code=response.status_code, body=response.text[:500]))

        payload = response.json()
        self._token = payload.get('access_token')
        self._token_expires_at = now + int(payload.get('expires_in', 3600)) - 60
        if not self._token:
            raise GoogleClientError(_("Google returned no access token."))
        return self._token

    def _post(self, url, body):
        try:
            response = requests.post(
                url,
                json=body,
                headers={'Authorization': 'Bearer %s' % self._access_token()},
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout:
            raise GoogleClientError(
                _("Google did not answer within %s seconds.", self.timeout))
        except requests.exceptions.RequestException as error:
            raise GoogleClientError(_("Could not reach Google: %s", error))

        if response.status_code == 403:
            raise GoogleClientError(_(
                "Google denied access (403). Add %s as a user with read access "
                "on the Search Console property and the GA4 property.",
                self.client_email))
        if response.status_code != 200:
            raise GoogleClientError(_(
                "Google returned HTTP %(code)s: %(body)s",
                code=response.status_code, body=response.text[:500]))
        try:
            return response.json()
        except ValueError:
            raise GoogleClientError(_("Google returned a non-JSON response."))

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def search_console(self, spec):
        """Run a Search Analytics query, return a list of flat rows."""
        if not self.gsc_site_url:
            raise GoogleClientError(
                _("No Search Console site is configured on this account."))
        dimensions = list(spec.get('dimensions') or ['query'])
        body = {
            'startDate': spec['start_date'],
            'endDate': spec['end_date'],
            'dimensions': dimensions,
            'rowLimit': spec.get('limit') or 25,
        }
        filters = spec.get('filters') or []
        if filters:
            body['dimensionFilterGroups'] = [{'filters': [
                {
                    'dimension': item['dimension'],
                    'operator': item['operator'],
                    'expression': item['expression'],
                }
                for item in filters
            ]}]

        url = GSC_ENDPOINT % urllib.parse.quote(self.gsc_site_url, safe='')
        payload = self._post(url, body)

        rows = []
        for row in payload.get('rows', []):
            flat = dict(zip(dimensions, row.get('keys', [])))
            for metric in GSC_METRICS:
                if metric in row:
                    flat[metric] = row[metric]
            rows.append(flat)
        return rows

    def analytics(self, spec):
        """Run a GA4 report, return a list of flat rows."""
        if not self.ga4_property_id:
            raise GoogleClientError(
                _("No Analytics property is configured on this account."))
        dimensions = list(spec.get('dimensions') or ['date'])
        metrics = list(spec.get('metrics') or ['sessions'])
        body = {
            'dateRanges': [{
                'startDate': spec['start_date'],
                'endDate': spec['end_date'],
            }],
            'dimensions': [{'name': name} for name in dimensions],
            'metrics': [{'name': name} for name in metrics],
            'limit': spec.get('limit') or 25,
        }

        expressions = []
        for item in spec.get('filters') or []:
            match_type, negate = GA4_MATCH_TYPES[item['operator']]
            expression = {'filter': {
                'fieldName': item['dimension'],
                'stringFilter': {
                    'matchType': match_type,
                    'value': item['expression'],
                    'caseSensitive': False,
                },
            }}
            expressions.append(
                {'notExpression': expression} if negate else expression)
        if expressions:
            body['dimensionFilter'] = {'andGroup': {'expressions': expressions}}

        order_by = spec.get('order_by')
        if order_by in metrics:
            body['orderBys'] = [{'metric': {'metricName': order_by},
                                 'desc': True}]

        payload = self._post(GA4_ENDPOINT % self.ga4_property_id, body)

        dimension_names = [
            header['name'] for header in payload.get('dimensionHeaders', [])]
        metric_names = [
            header['name'] for header in payload.get('metricHeaders', [])]
        rows = []
        for row in payload.get('rows', []):
            flat = {}
            for name, value in zip(dimension_names, row.get('dimensionValues', [])):
                flat[name] = value.get('value')
            for name, value in zip(metric_names, row.get('metricValues', [])):
                flat[name] = value.get('value')
            rows.append(flat)
        return rows


def _normalise_property(property_id):
    """Accept '123456' as readily as 'properties/123456'."""
    property_id = (property_id or '').strip()
    if not property_id:
        return ''
    if property_id.startswith('properties/'):
        return property_id
    return 'properties/%s' % property_id.lstrip('/')


def validate_spec(spec, source_available):
    """Check a generated query spec before anything is sent to Google.

    Returns the cleaned spec. Raises GoogleClientError naming the offending
    value, so the user can rephrase the question.
    """
    if not isinstance(spec, dict):
        raise GoogleClientError(_("The AI did not return a query object."))

    source = spec.get('source') or SOURCE_SEARCH_CONSOLE
    if source not in (SOURCE_SEARCH_CONSOLE, SOURCE_ANALYTICS, 'both'):
        raise GoogleClientError(_("Unknown data source '%s'.", source))
    for wanted in _sources(source):
        if not source_available.get(wanted):
            raise GoogleClientError(_(
                "The question needs %s, which is not configured on this "
                "Google account.", wanted))

    for date_field in ('start_date', 'end_date'):
        if not spec.get(date_field):
            raise GoogleClientError(_("The query is missing %s.", date_field))

    limit = spec.get('limit') or DEFAULT_ROWS
    try:
        limit = max(1, min(int(limit), MAX_ROWS))
    except (TypeError, ValueError):
        limit = DEFAULT_ROWS
    # Results come back best-first, so a small limit on a multi-dimension query
    # returns the top term repeated per breakdown value and nothing else.
    if len(spec.get('dimensions') or []) > 1:
        limit = max(limit, MAX_ROWS)
    spec['limit'] = limit

    for wanted in _sources(source):
        allowed_dimensions = (
            GSC_DIMENSIONS if wanted == SOURCE_SEARCH_CONSOLE else GA4_DIMENSIONS)
        allowed_metrics = (
            GSC_METRICS if wanted == SOURCE_SEARCH_CONSOLE else GA4_METRICS)
        for dimension in spec.get('dimensions') or []:
            if dimension not in allowed_dimensions:
                raise GoogleClientError(_(
                    "'%(name)s' is not a dimension available on %(source)s.",
                    name=dimension, source=wanted))
        for metric in spec.get('metrics') or []:
            if metric not in allowed_metrics:
                raise GoogleClientError(_(
                    "'%(name)s' is not a metric available on %(source)s.",
                    name=metric, source=wanted))

    for item in spec.get('filters') or []:
        if not isinstance(item, dict):
            raise GoogleClientError(_("A filter is not an object."))
        if item.get('operator') not in FILTER_OPERATORS:
            raise GoogleClientError(_(
                "'%(op)s' is not a supported filter operator. Use one of: "
                "%(allowed)s.",
                op=item.get('operator'), allowed=', '.join(FILTER_OPERATORS)))
        if not item.get('dimension') or item.get('expression') is None:
            raise GoogleClientError(
                _("A filter is missing its dimension or expression."))

    return spec


def _sources(source):
    if source == 'both':
        return [SOURCE_SEARCH_CONSOLE, SOURCE_ANALYTICS]
    return [source]


def _format_value(column, value):
    """Keep the table readable: raw API floats run to 16 decimal places."""
    if isinstance(value, str):
        try:
            value = float(value) if '.' in value else int(value)
        except ValueError:
            return value
    if isinstance(value, float):
        if column == 'ctr':
            return '%.2f%%' % (value * 100)
        if column in ('position', 'engagementRate', 'bounceRate',
                      'averageSessionDuration'):
            return '%.2f' % value
        return ('%.2f' % value).rstrip('0').rstrip('.')
    return str(value)


def rows_to_table(rows, limit_chars):
    """Render rows as a compact text table for the AI to read."""
    if not rows:
        return _("(no rows returned)")
    columns = list(rows[0].keys())
    lines = [' | '.join(columns)]
    for row in rows:
        lines.append(' | '.join(
            _format_value(column, row.get(column, '')) for column in columns))
        if sum(len(line) for line in lines) > limit_chars:
            lines.append(_('... truncated ...'))
            break
    return '\n'.join(lines)


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
# The credentials live in system parameters, set from Settings > AI Page
# Builder. They are read in sudo: the settings are administrator-only, but any
# user allowed to ask a question may have their question answered.
PARAM_SERVICE_ACCOUNT = 'cap_website_builder.google_service_account_json'
PARAM_GSC_SITE = 'cap_website_builder.gsc_site_url'
PARAM_GA4_PROPERTY = 'cap_website_builder.ga4_property_id'


def google_config(env):
    params = env['ir.config_parameter'].sudo()
    return {
        'service_account_json': params.get_param(PARAM_SERVICE_ACCOUNT) or '',
        'gsc_site_url': params.get_param(PARAM_GSC_SITE) or '',
        'ga4_property_id': params.get_param(PARAM_GA4_PROPERTY) or '',
    }


def available_sources(env):
    """Which of the two services the configuration can actually query."""
    config = google_config(env)
    return {
        'search_console': bool(config['gsc_site_url']),
        'analytics': bool(config['ga4_property_id']),
    }


def get_client(env):
    config = google_config(env)
    if not config['service_account_json']:
        raise GoogleClientError(_(
            "No Google service account key configured. Add one in Settings > "
            "AI Page Builder."))
    return GoogleClient(
        config['service_account_json'],
        gsc_site_url=config['gsc_site_url'],
        ga4_property_id=config['ga4_property_id'],
    )


def service_account_email(env):
    """The address that needs read access on the Google properties."""
    key = google_config(env)['service_account_json']
    if not key:
        return ''
    try:
        return json.loads(key).get('client_email') or ''
    except ValueError:
        return ''
