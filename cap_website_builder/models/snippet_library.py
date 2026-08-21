"""A fallback palette of real Odoo 19 snippets.

When a page request names a reference page, that page is the palette: its own
blocks are sent as examples and the AI rebuilds them with new words. With no
reference there is nothing to copy from, and a model left to its own devices
writes bare ``<h1>`` and ``<p>`` tags - correct content in a page the website
editor cannot edit block by block.

These templates are copied from ``website/views/snippets/*.xml``, with the QWeb
attributes (``t-att-href``, ``t-out``) resolved to plain markup and the
``data-snippet`` / ``data-name`` attributes the editor writes when a block is
dropped. Keep them in step with the addon: a class the theme does not know
renders as unstyled markup, which is the very problem this file exists to fix.

Every template here must be valid XML - Odoo stores a view arch as XML, so a
bare ``<img>`` would fail the whole page.
"""

# Friendly name -> full markup of one block.
SNIPPETS = {
    's_title': """<section class="s_title pt40 pb40" data-vcss="001" data-snippet="s_title" data-name="Title">
    <div class="container s_allow_columns">
        <h2 class="display-3-fs">Your section title</h2>
    </div>
</section>""",

    's_text_block': """<section class="s_text_block pt40 pb40" data-snippet="s_text_block" data-name="Text">
    <div class="container s_allow_columns">
        <p>A paragraph of real copy about the subject.</p>
        <p>A second paragraph, saying something the first did not.</p>
    </div>
</section>""",

    's_text_image': """<section class="s_text_image pt80 pb80" data-snippet="s_text_image" data-name="Text - Image">
    <div class="container">
        <div class="row align-items-center">
            <div class="col-lg-5 pt16 pb16">
                <h2 class="h3-fs">A heading with a <strong>strong word</strong></h2>
                <p>A paragraph explaining this section.</p>
                <p><a href="#" class="btn btn-primary">Learn more</a></p>
            </div>
            <div class="col-lg-6 offset-lg-1 pt16 pb16">
                <img src="/web/image/website.s_text_image_default_image" class="img img-fluid mx-auto rounded" alt=""/>
            </div>
        </div>
    </div>
</section>""",

    's_image_text': """<section class="s_text_image pt80 pb80" data-snippet="s_image_text" data-name="Image - Text">
    <div class="container">
        <div class="row align-items-center">
            <div class="col-lg-6 pt16 pb16">
                <img src="/web/image/website.s_image_text_default_image" class="img img-fluid mx-auto rounded" alt=""/>
            </div>
            <div class="col-lg-5 offset-lg-1 pt16 pb16">
                <h2 class="h3-fs">A heading with a <strong>strong word</strong></h2>
                <p>A paragraph explaining this section.</p>
                <p><a href="#" class="btn btn-primary">Learn more</a></p>
            </div>
        </div>
    </div>
</section>""",

    's_features': """<section class="s_features pt64 pb64" data-snippet="s_features" data-name="Features">
    <div class="container">
        <h2 class="h3-fs">A heading over the three points</h2>
        <p class="lead">One line introducing them.</p>
        <div class="row">
            <div class="col-lg-4">
                <div class="s_hr pt-4 pb32">
                    <hr class="w-100 mx-auto"/>
                </div>
                <i class="s_features_icon fa fa-paper-plane-o mb-3 rounded bg-o-color-3" role="img"></i>
                <div class="overflow-hidden">
                    <h3 class="h5-fs">First point</h3>
                    <p>What it means, in a sentence or two.</p>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="s_hr pt-4 pb32">
                    <hr class="w-100 mx-auto"/>
                </div>
                <i class="s_features_icon fa fa-credit-card mb-3 rounded bg-o-color-3" role="img"></i>
                <div class="overflow-hidden">
                    <h3 class="h5-fs">Second point</h3>
                    <p>What it means, in a sentence or two.</p>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="s_hr pt-4 pb32">
                    <hr class="w-100 mx-auto"/>
                </div>
                <i class="s_features_icon fa fa-flag-o mb-3 rounded bg-o-color-3" role="img"></i>
                <div class="overflow-hidden">
                    <h3 class="h5-fs">Third point</h3>
                    <p>What it means, in a sentence or two.</p>
                </div>
            </div>
        </div>
    </div>
</section>""",

    's_call_to_action': """<section class="s_call_to_action o_cc o_cc5 pt64 pb64" data-snippet="s_call_to_action" data-name="Call to Action">
    <div class="container">
        <div class="row">
            <div class="col-lg-9">
                <h2 class="h3-fs">The one thing you want the reader to do.</h2>
                <p class="lead">One line of encouragement.</p>
            </div>
            <div class="col-lg-3">
                <p><a href="/contactus" class="btn btn-primary btn-lg">Contact us</a></p>
            </div>
        </div>
    </div>
</section>""",
}

# What each block is for, so the model picks by purpose rather than by name.
PURPOSE = {
    's_title': "a section heading on its own, between two blocks",
    's_text_block': "one or two paragraphs of prose, no image",
    's_text_image': "a section whose copy sits left of an image",
    's_image_text': "a section whose copy sits right of an image",
    's_features': "exactly three short points - use it for a bullet list of three",
    's_call_to_action': "the closing block that tells the reader what to do next",
}

INTRO = """=== THE ONLY BLOCK TYPES YOU MAY USE ===
This site has no reference page, so build the page from these standard Odoo
snippets and no others. Start from a block's markup and change only the words
inside the text nodes. Keep everything else byte for byte: the s_* class, the
data-snippet and data-name attributes, the o_cc colour classes, the pt/pb
spacing classes, and the container / row / col-lg-* nesting. That markup is
what makes the block editable in the website editor and styled by the theme -
a bare <h1> or <p> is neither.

%(purposes)s

Turning the copy into blocks:
- The H1 line opens the page. Keep it as an <h1> inside the first section.
- Every "## " heading starts a new section. Do not put two of them in one block.
- Alternate the blocks: never three of the same type in a row. A page of nothing
  but s_text_block is the failure this list exists to prevent.
- A list of about three items becomes s_features. A longer list stays a <ul>
  inside s_text_block.
- The last section becomes s_call_to_action.
- Images: only the URLs written in the examples below. Any other path renders as
  a broken image. If a block does not suit an image, use a block without one.

=== FULL MARKUP, ONE EXAMPLE PER BLOCK TYPE ===
%(examples)s
"""


# The blocks built around a picture. Generated pages are text only, so these
# are left out rather than offered empty: a text page is built from blocks meant
# for text.
IMAGE_SNIPPETS = ('s_text_image', 's_image_text')


def fallback_palette():
    """The block list, purposes and full markup, ready to paste into a prompt."""
    keys = [key for key in SNIPPETS if key not in IMAGE_SNIPPETS]
    purposes = '\n'.join('- %s: %s' % (key, PURPOSE[key]) for key in keys)
    examples = '\n\n'.join(
        '<!-- snippet: %s -->\n%s' % (key, SNIPPETS[key]) for key in keys)
    return INTRO % {'purposes': purposes, 'examples': examples}
