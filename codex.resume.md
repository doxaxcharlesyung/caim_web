# CAIM Web Resume

Current state:

- CAIM is deployed as a dedicated site at `caim.doxaxsolutions.com`.
- PROD content is served from `/opt/caim_web`.
- `test.doxaxsolutions.com` remains separate and is served from `/opt/test.doxaxsolutions.com`.
- The CAIM Apache vhost proxies to the dedicated CAIM service on `127.0.0.1:18003`.
- The site includes paired English and Traditional Chinese pages.
- The language toggle uses `EN` and `ZH`, with `ZH` linking to the matching Chinese page and `EN` linking back.

Important files:

- `home.html`
- `zh_home.html`
- `dx_sermon.html`
- `zh_dx_sermon.html`
- `ai_courses.html`
- `zh_ai_courses.html`
- `workshop.html`
- `zh_workshop.html`
- `how_to_help.html`
- `zh_how_to_help.html`
- `site.css`
- `app.py`
- `.github/workflows/deploy-prod.yml`

Recent home-page work:

- Hero title changed to `Training the Church to Shepherd in a Digital Age`.
- Hero message changed to `Forming prayerful, discerning leaders who integrate faith, wisdom, and AI for Christ-centered ministry.`
- Traditional Chinese hero copy updated in `zh_home.html`.
- Home page service tiles were removed.
- Home page article section now uses a 3-column image-card layout.
- Home page FAQ now uses an accordion row layout with plus markers.

Help page work:

- `Current boundary` tile removed from `how_to_help.html`.
- The same boundary note was removed from `zh_how_to_help.html`.

Workshop work:

- `workshop.html` was rebuilt to match the source CAIM workshop section.
- Local CAIM-owned assets were added for the banner and seminar posters.

DX Sermon work:

- The missionary discount message is presented as a prominent banner.

Deployment and verification notes:

- Live CAIM pages were verified after each major change with `200` responses.
- UTF-8 rendering for the Chinese pages was verified with no replacement characters.
- Do not touch PROD without explicit approval for that specific action.

Recent commit landmarks:

- `e9fe16c` - Remove help boundary note
- `850a52a` - Match FAQ accordion layout
- `328504a` - Refresh home articles and FAQ layout
- `6291d16` - Update CAIM home hero copy
- `648a265` - Add Traditional Chinese CAIM pages

Working tree note:

- `.idea/` remains untracked and is intentionally left alone.
