# Brief

Main challenge, 14 Nov. Same brief as the warm-up; built from scratch with the lessons from the warm-up report (90.5). Owner: edit anything here before `/pw-plan`.

## Challenge (copied word for word)

Develop an AI-driven civic intelligence solution that enables local authorities, housing societies, and ward-level teams to turn raw air quality data into actionable local interventions. The solution must leverage Generative AI as a core component to interpret pasted or uploaded data tables, including messy ones with inconsistent formats, units, or missing readings, and summarize trends and likely hotspots in plain language. It should recommend prioritized local actions suited to who is asking, since a ward officer, a housing society, and a school can each do different things. Every finding should be traceable to the underlying data, with data gaps and unreliable readings clearly flagged. The assistant should compare each new brief with the previous one to show what changed, and generate both an internal briefing note and a citizen advisory in multiple languages, written for different reading levels, with extra care for children, older adults, and people sensitive to poor air.

## Every ask, mapped to a feature

| Ask in the challenge | Feature |
|---|---|
| Paste or upload messy tables (formats, units, missing readings) | Paste box + CSV upload; parsed with `csv.Sniffer`, units normalised in `logic.py` |
| Trends and likely hotspots in plain language | Lead line + Hotspots section |
| Prioritised actions suited to who is asking | Role picker (ward officer, housing society, school); actions ranked, each with who, what, by when |
| Every finding traceable to the data | Source chip on every finding ("Row 14 · TT Nagar") plus a "Cleaned data" table with row numbers |
| Data gaps and unreliable readings flagged | Data trust panel: missing and impossible readings (>999, negative, wrong unit); findings that rely on them marked low confidence |
| Compare each new brief with the previous one | "Since last brief" section; previous brief kept in the signed session, never a global variable |
| Internal briefing note | Printable A4 note, behind a simple staff sign-in |
| Citizen advisory, multiple languages, reading levels | Phone-sized advisory card; English, Hindi and Urdu (Gemini writes all three, so "multiple" is met); simple and standard reading levels |
| Extra care for children, older adults, sensitive people | Separate plain lines for each group in the advisory |

## The one user
Ravi, an assistant engineer for one Bhopal ward. Every Monday he gets a messy sheet from 3 monitors and has about 15 minutes before the ward review to decide what to do this week.
Secondary: the secretary of a housing society and a school principal, who get the citizen advisory.

## Device
Desk (Ravi, at the ward office). The citizen advisory is read on phones, so it is previewed as a phone-sized card.

## Their pain, backed by data
- **The data is unreliable.** Only 270 of India's 562 live monitoring stations gave stable data in 2025; the rest had gaps or interruptions, and 58 were rated unstable (Airvoice, via ThePrint). Delhi: 45 of 59 stations missed hourly readings; PM readings above 999 are left out of the AQI (Free Press Journal).
- **Money exists, action doesn't.** Delhi's municipal corporation spent 17% of its clean air funds in 5 years (Tribune, RTI). Bengaluru has over ₹250 crore unused and an action plan not updated since 2019 (Citizen Matters). Experts blame a lack of local expertise (BQ Prime).
- **Bhopal.** ₹242 crore released under NCAP, ₹195 crore spent, still 6th in the clean air survey (Free Press Journal). Dust is 62% of PM10 (state report to the NGT). Named causes: Smart City construction dust, Bhanpur landfill burning, night-time waste burning, 1.3 million vehicles; winter nights above AQI 300.
- **Citizens don't understand AQI.** 93% of Delhi residents don't understand AQI or its categories (India TV survey). Only 10% of the urban poor know the terms AQI or PM2.5 (Chintan, via Business Standard). People trust newspapers (70%) more than government sites (26%).

Sources for the README's "Why this matters":
- https://theprint.in/environment/indian-districts-air-quality-monitoring-station-airvoice/2893284
- https://www.tribuneindia.com/news/delhi/as-national-capital-chokes-mcd-sat-on-clean-air-funds
- https://www.freepressjournal.in/bhopal/clean-air-survey-despite-190-crore-spend-bhopal-stuck-at-6th-rank
- https://www.indiatvnews.com/news/india-93-per-cent-delhiites-don-t-know-what-aqi-means-survey-499958
- https://www.business-standard.com/india-news/air-pollution-related-terminologies-awareness-low-among-urban-poor-study-124040700353_1.html

## The golden path (what the demo shows)
1. Ravi loads the Bhopal example sheet (or pastes his own), picks "Ward officer", Hindi, simple.
2. The code cleans the table and flags gaps; Gemini writes the brief from the cleaned data, citing rows.
3. He gets: the lead line, the hotspot, 3 ranked actions with sources, what changed since last week, a printable internal note and a citizen advisory he can play in Hindi or send on WhatsApp.

## Screens (no sketch: build from this description, then the owner reviews what was created)
- Screen 1 (two panes): left, input (paste or upload, role, language, reading level, Analyse); right, the brief.
- Screen 2: the brief's sections: Hotspots, Actions, Data trust, Since last brief, Internal note (staff), Citizen advisory (phone card).
- The one line the result opens with, for example: "TT Nagar is the hotspot: PM2.5 up 40% since last week, likely construction dust." (The real line always comes from the data. Never hard-code it.)

## Priority (fewer features that all work)

**Core: all working and deployed by minute 90 (Submission 1).** Only the 9 asks above, in one flow: paste or upload, clean and flag, brief with sources, ranked actions by role, since last brief, internal note, citizen advisory in 3 languages and 2 reading levels. Staff sign-in for the internal note (the briefing asked for login on security grounds); the demo username and password go on the sign-in page, in the README and in the submission text.

**Stretch, in this order, only after Submission 1, each hidden if not working in 15 minutes:**
1. Hear it in Hindi (Cloud Text-to-Speech) on the advisory.
2. WhatsApp share link for the advisory.
3. Clicking a source chip highlights its row.
4. Flatlined sensor check (the same value 4+ times in a row).

**Not building:** maps, charts beyond one small trend bar, live sensor feeds, history beyond the previous brief, more roles, a chat box.

## Design direction
- A **briefing workspace**, not a dashboard and not a chat. Input left, a structured document right.
- **India's AQI scale** (CPCB's 6 categories: Good, Satisfactory, Moderate, Poor, Very Poor, Severe). Always colour + label + number. Colour means AQI only, never decoration.
- **Source chips** on every finding; **trust badges** (high, low confidence) with words, not colour alone.
- **Since last brief:** arrows plus words ("worse", "better", "new").
- **Internal note:** clean A4 document with print styles. **Citizen advisory:** phone-sized card, plain words, no AQI jargon ("Keep children indoors after 6 pm"). Listen and WhatsApp buttons only if those stretch items ship.
- Calm government tone in the spirit of India's UX4G and GOV.UK: white space, one accent, no gradients.

## How Gemini is used, and why AI is needed here
- Reads the cleaned table and its flags, then writes the trend, hotspots and role-specific ranked actions, each citing row IDs (the code drops any finding whose rows weren't sent).
- Writes the internal note and the citizen advisory in the chosen language and reading level, with lines for children, older adults and sensitive people.

## What the code does, not the AI
- Parses messy tables with `csv.Sniffer`; normalises units (mg/m³ to µg/m³); detects missing and impossible readings.
- Computes averages, peaks, the AQI category per reading, and the change since the previous brief.
- Validates every citation against the parsed rows.

## X factor (one, from /pw-xfactor)
- What: **Hear it in Hindi** (Cloud Text-to-Speech) on the citizen advisory, plus a WhatsApp share link.
- The barrier it removes: most citizens can't read AQI terms, and many can't read long text.
- The 10-second demo: tap Listen on the advisory card and the room hears it in Hindi.

## Google services
- Gemini API: the brief, actions, note and advisory
- Cloud Text-to-Speech: Hindi audio for the advisory
- Cloud Run: hosting
- Secret Manager: the API key
- Cloud Logging: request logs

## Out of scope today
- Maps, live sensor feeds, a database, user accounts beyond one staff sign-in, payments
