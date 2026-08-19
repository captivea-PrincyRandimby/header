# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Prefill the per-language logo table for every website with its current
    logo, one row per active language on that website."""
    env['website'].search([]).action_generate_lang_logos()
