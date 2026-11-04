# Blog Automation — Style Guide

Applies to every article generated for theworldin.wordpress.com daily series.

## Voice
- First person, professional, plain-spoken. Timothy's existing voice: short intro,
  clear section headers (`<h2>`), practical explanations, honest takeaways.
- No hype, no buzzword stuffing. Explain like an engineer talking to a smart peer.
- 600–900 words. Headers break up the text; short paragraphs.

## Honesty rules (hard requirements)
- Every claim about Timothy's background must match what he has actually stated:
  - Systems Manager & Applications Engineer; background in applications/systems
    engineering, data integration, systems management.
  - Azure PaaS/SaaS, Automation runbooks, PowerShell, Python. IaaS conceptual only.
  - "Elevation" = privileged-access elevation gated by MFA + peer approval.
  - Power BI + Microsoft Fabric: managed workspaces, pipelines/dataflows, capacity admin.
  - GCP: shared web hosting / in-house development. AWS Lambda (roku project) exists
    but is not his core story.
  - Grafana dashboards: prior hands-on experience.
- Frame the entrepreneur series as exploration + thought leadership, NOT as claims
  of running a large business. Honest framing: "As an engineer exploring the
  independent path..." He is job-searching for remote-only roles; the series
  markets his availability. Never invent clients, revenue, or companies.
- The JobApplicationEngine "human gates" lesson (some steps need a person: CAPTCHAs,
  verification codes, dropdown selections) is fair game as an authentic story.

## Structure
1. Title (clear, no clickbait, no emojis).
2. Opening: one personal or observational hook, 2–3 sentences.
3. 3–5 `<h2>` sections developing the idea, each tied to a real engineering
   concept from his background where natural.
4. Closing: 2–3 sentence takeaway.
5. Availability CTA (exact block below), lightly adapted if the article topic
   suggests a tweak — never dropped.

## Availability CTA (append verbatim unless lightly adapted)
```html
<hr>
<p><em>I'm Timothy Webb, a Systems Manager &amp; Applications Engineer based in
South Carolina, working 100% remote. I build data integrations, automation, and
reliable systems — and I'm currently open to remote opportunities in applications
engineering, data engineering, and systems management. You can read more about
my background here: <a href="https://theworldin.wordpress.com/2026/08/04/%f0%9f%9a%80-engineering-the-future/">Why I'm Ready for My Next Role</a>.</em></p>
```

## Series continuity
- This is a 30-article series on "The Independent Entrepreneur in 2026" /
  AI-native solopreneurship. Each article should stand alone but may reference
  earlier series entries or his existing case studies (EA/OpenAPI, Spark ETL,
  MLflow) with links where genuinely relevant.
- Queue files live in `queue/` as `NN-slug.md`: first line `TITLE: <title>`,
  blank line, then the HTML body (`<h2>`, `<p>`, `<ul>/<li>`, `<hr>`, `<em>`).
  ASCII only in code contexts; standard punctuation elsewhere is fine.
