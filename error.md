# Errors & Solutions

1) **Error:** The CRM lead title is always `Form - {Short title of the page}` because the hidden Subject field has a hardcoded placeholder value.
**Solution:** Make it dynamic from the page URL path.

2) **Error:** The visitor's message lands in the lead notes under `Other information` instead of the lead description, because the textarea is a custom field named `Your Project`.
**Solution:** Rename the field to `description`.

3) **Error:** `country_id` and `source_id` are dumped in the notes as raw IDs instead of being saved, because they are not form-writable on `crm.lead`.
**Solution:** Whitelist them with `formbuilder_whitelist`.

4) **Error:** The country select has no empty option, so a visitor who never touches it silently submits Afghanistan (the first entry).
**Solution:** Add an empty first option.

5) **Error:** The hidden `source_id` field is hardcoded to `1` (Search engine), which forces the same source on every lead and breaks marketing attribution.
**Solution:** Remove the hidden UTM fields and let `utm.mixin` fill them from the UTM cookies.
