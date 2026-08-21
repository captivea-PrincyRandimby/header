"""Provider agnostic LLM access layer.

These are plain Python classes, not Odoo models: they only need the
configuration parameters, and keeping them out of the ORM makes them easy to
call from anywhere in the module.
"""
import logging
import time

import requests

from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

# A page's worth of copy against a full Surfer brief runs past three minutes on
# a large model. The old 180s cut those requests off mid-answer.
DEFAULT_TIMEOUT = 600
DEFAULT_MAX_TOKENS = 16000
ANTHROPIC_VERSION = '2023-06-01'

# Anthropic runs the search itself and bills per search, so the model is given
# a hard budget rather than being left to decide how many it wants.
WEB_SEARCH_TOOL = 'web_search_20250305'
WEB_SEARCH_MAX_USES = 5

# Tokens kept free for the answer when extended thinking is switched on.
ANSWER_HEADROOM = 8000

# OpenAI's reasoning models reject `max_tokens` outright and want
# `max_completion_tokens`, because reasoning and the answer share one budget -
# the same arrangement that returned an empty answer on Anthropic. Matched on
# the model id, since that is the only thing the endpoint tells us in advance.
REASONING_MODEL_PREFIXES = ('gpt-5', 'o1', 'o3', 'o4')

# Providers shed load under pressure: Anthropic answers 529 "overloaded", and
# 429 is a rate limit. Both are transient and worth waiting out - losing a
# whole pipeline to one busy moment costs far more than a few seconds here.
RETRY_STATUSES = (429, 500, 502, 503, 504, 529)
RETRY_ATTEMPTS = 4
RETRY_BACKOFF = 5  # seconds, doubled each attempt: 5, 10, 20


class AIProviderError(Exception):
    """Raised for anything that went wrong while talking to the provider.

    Callers catch this and report it in the chatter instead of letting a
    traceback dialog destroy the user's prompt.
    """


class AIProvider:
    """Base class. Subclasses only implement :meth:`chat`."""

    name = None

    # Whether the provider can search the web during a request. Only Anthropic
    # exposes a server-side search tool; everywhere else the model answers from
    # what it already knows.
    supports_web_search = False

    def __init__(self, api_key, model, base_url=None, timeout=DEFAULT_TIMEOUT,
                 max_tokens=DEFAULT_MAX_TOKENS, thinking_budget=0):
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or '').rstrip('/')
        self.timeout = timeout or DEFAULT_TIMEOUT
        self.max_tokens = max_tokens or DEFAULT_MAX_TOKENS
        self.thinking_budget = thinking_budget or 0

    def chat(self, system, messages, web_search=False):
        """Send a conversation and return the assistant answer as text.

        :param str system: system prompt
        :param list messages: ``[{'role': 'user'|'assistant', 'content': str}]``
        :param bool web_search: let the model search the web, when it can.
            Providers without the capability ignore it rather than failing.
        :rtype: str
        """
        raise NotImplementedError

    def _post(self, url, headers, payload):
        delay = RETRY_BACKOFF
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                response = requests.post(
                    url, headers=headers, json=payload, timeout=self.timeout)
            except requests.exceptions.Timeout:
                raise AIProviderError(_(
                    "The AI provider did not answer within %s seconds.",
                    self.timeout))
            except requests.exceptions.RequestException as error:
                raise AIProviderError(
                    _("Could not reach the AI provider: %s", error))

            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError:
                    raise AIProviderError(
                        _("The AI provider returned a non-JSON response."))

            if response.status_code in RETRY_STATUSES and attempt < RETRY_ATTEMPTS:
                # Honour Retry-After when the provider sends one, since it
                # knows better than any backoff we invent.
                wait = delay
                header = response.headers.get('Retry-After')
                if header:
                    try:
                        wait = max(wait, int(float(header)))
                    except ValueError:
                        pass
                _logger.warning(
                    "AI provider returned HTTP %s, retrying in %ss (%s/%s)",
                    response.status_code, wait, attempt, RETRY_ATTEMPTS)
                time.sleep(wait)
                delay *= 2
                continue

            raise AIProviderError(_(
                "The AI provider returned HTTP %(code)s: %(body)s",
                code=response.status_code, body=response.text[:1000],
            ))


class MistralProvider(AIProvider):
    name = 'mistral'
    endpoint = 'https://api.mistral.ai/v1/chat/completions'

    def chat(self, system, messages, web_search=False):
        payload = {
            'model': self.model or 'mistral-large-latest',
            'max_tokens': self.max_tokens,
            'messages': [{'role': 'system', 'content': system}] + messages,
        }
        headers = {
            'Authorization': 'Bearer %s' % self.api_key,
            'Content-Type': 'application/json',
        }
        data = self._post(self.endpoint, headers, payload)
        try:
            return data['choices'][0]['message']['content'] or ''
        except (KeyError, IndexError, TypeError):
            raise AIProviderError(_("Unexpected answer from Mistral: %s", data))


class AnthropicProvider(AIProvider):
    name = 'anthropic'
    endpoint = 'https://api.anthropic.com/v1/messages'
    supports_web_search = True

    def chat(self, system, messages, web_search=False):
        payload = {
            'model': self.model or 'claude-opus-5',
            'max_tokens': self.max_tokens,
            'system': system,
            'messages': messages,
        }
        # Extended thinking shares the max_tokens budget with the answer. Left
        # on, a model asked to satisfy 81 term ranges at once spends the whole
        # budget reasoning and stops at max_tokens having written nothing: the
        # request looks like a timeout and costs a full budget of tokens.
        if self.thinking_budget:
            payload['thinking'] = {
                'type': 'enabled', 'budget_tokens': self.thinking_budget}
            # The answer needs room of its own on top of the thinking budget.
            payload['max_tokens'] = max(
                self.max_tokens, self.thinking_budget + ANSWER_HEADROOM)
        else:
            payload['thinking'] = {'type': 'disabled'}
        if web_search:
            # A server tool: Anthropic runs the searches and feeds the results
            # back to the model itself, so there is no tool loop to run here.
            payload['tools'] = [{
                'type': WEB_SEARCH_TOOL,
                'name': 'web_search',
                'max_uses': WEB_SEARCH_MAX_USES,
            }]
        headers = {
            'x-api-key': self.api_key,
            'anthropic-version': ANTHROPIC_VERSION,
            'Content-Type': 'application/json',
        }
        data = self._post(self.endpoint, headers, payload)
        try:
            blocks = data['content']
        except (KeyError, TypeError):
            raise AIProviderError(_("Unexpected answer from Anthropic: %s", data))
        # Search requests and their results arrive as extra blocks; only the
        # model's own words are the answer.
        return ''.join(block.get('text', '') for block in blocks if block.get('type') == 'text')


class OpenAICompatibleProvider(AIProvider):
    """Works with OpenAI itself and with anything exposing the same route
    (Ollama, vLLM, LiteLLM, Azure-style gateways...)."""

    name = 'openai_compatible'

    def _is_reasoning_model(self):
        model = (self.model or '').lower()
        return model.startswith(REASONING_MODEL_PREFIXES)

    def chat(self, system, messages, web_search=False):
        if not self.base_url:
            raise AIProviderError(
                _("No base URL configured for the OpenAI-compatible provider."))
        payload = {
            'model': self.model,
            'messages': [{'role': 'system', 'content': system}] + messages,
        }
        if self._is_reasoning_model():
            # One budget covers the reasoning and the answer, so it has to be
            # generous or the model thinks its way to an empty reply.
            payload['max_completion_tokens'] = max(
                self.max_tokens, ANSWER_HEADROOM)
            # Thinking Budget is a switch here rather than a token count: 0
            # means "answer, do not deliberate", which is what page copy wants.
            payload['reasoning_effort'] = 'low' if not self.thinking_budget \
                else 'high' if self.thinking_budget > 8000 else 'medium'
        else:
            payload['max_tokens'] = self.max_tokens
        headers = {
            'Authorization': 'Bearer %s' % self.api_key,
            'Content-Type': 'application/json',
        }
        data = self._post(self.base_url + '/chat/completions', headers, payload)
        try:
            choice = data['choices'][0]
            content = choice['message']['content'] or ''
        except (KeyError, IndexError, TypeError):
            raise AIProviderError(
                _("Unexpected answer from the AI provider: %s", data))
        if not content.strip() and choice.get('finish_reason') == 'length':
            # The Anthropic lesson, in OpenAI's dialect: a reasoning model can
            # spend the whole budget deliberating and return nothing at all.
            raise AIProviderError(_(
                "The model used its whole token budget before writing "
                "anything. Raise Max Tokens on the AI model, or lower its "
                "Thinking Budget."))
        return content


PROVIDERS = {
    'mistral': MistralProvider,
    'anthropic': AnthropicProvider,
    'openai_compatible': OpenAICompatibleProvider,
}


def get_provider(ai_model):
    """Build a provider from a ``cap.ai.model`` record.

    Read in sudo: the API key is restricted to settings administrators, but any
    user allowed to build pages may use the model.
    """
    if not ai_model:
        raise AIProviderError(_(
            "No AI model selected. Create one in AI Page Builder > "
            "Configuration > AI Models."))
    ai_model = ai_model.sudo()

    provider_class = PROVIDERS.get(ai_model.provider)
    if not provider_class:
        raise AIProviderError(_("Unknown AI provider '%s'.", ai_model.provider))
    if not ai_model.api_key:
        raise AIProviderError(_(
            "The AI model '%s' has no API key. Set it in AI Page Builder > "
            "Configuration > AI Models.", ai_model.display_name))

    return provider_class(
        api_key=ai_model.api_key,
        model=ai_model.model_name,
        base_url=ai_model.base_url,
        timeout=ai_model.timeout or DEFAULT_TIMEOUT,
        max_tokens=ai_model.max_tokens or DEFAULT_MAX_TOKENS,
        thinking_budget=ai_model.thinking_budget,
    )
