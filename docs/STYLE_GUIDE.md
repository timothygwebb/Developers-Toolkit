# Blog Automation — Style Guide (template)

Use this file as a template for a daily WordPress poster. Replace every
placeholder in [brackets] with your own site, voice, and background.
Example site: your-site.wordpress.com.

## Voice
- First person, professional, plain-spoken: short intro, clear section
  headers (`<h2>`), practical explanations, honest takeaways.
- No hype, no buzzword stuffing. Explain like an engineer talking to a smart peer.
- 600-900 words. Headers break up the text; short paragraphs.

## Honesty rules (hard requirements)
- Every claim about background must match what you have actually stated.
  Example template — replace with your own:
  - [Your role]; background in [your background areas].
  - Tools: [your tools]. Note what is conceptual only, if anything.
  - Do not claim tools, clients, revenue, or companies you do not have.
- Frame the series as exploration + thought leadership, NOT as claims
  of running a large business. Honest framing: "As an engineer exploring
  the independent path..." Never invent clients, revenue, or companies.
- A "human gates" lesson (some steps need a person: CAPTCHAs,
  verification codes, dropdown selections) is fair game as an authentic story.

## Structure
1. Title (clear, no clickbait, no emojis).
2. Opening: one personal or observational hook, 2-3 sentences.
3. 3-5 `<h2>` sections developing the idea, each tied to a real engineering
   concept where natural.
4. Closing: 2-3 sentence takeaway.
5. Availability CTA (exact block below), lightly adapted if the article topic
   suggests a tweak — never dropped.

## Availability CTA (template — replace placeholders, then append verbatim)
```html
<hr>
<p><em>I'm [Your Name], a [Your Role] based in [Your Location], working [remote/onsite]. I build [what you build] — and I'm currently open to [opportunities you are open to]. You can read more about my background here: <a href="https://example.com/about">About</a>.</em></p>
```

## Series continuity
- This is a 30-article series template. Each article should stand alone but
  may reference earlier series entries or existing case studies with links
  where genuinely relevant.
- Queue files live in `queue/` as `NN-slug.md`: first line `TITLE: <title>`,
  blank line, then the HTML body (`<h2>`, `<p>`, `<ul>/<li>`, `<hr>`, `<em>`).
  ASCII only in code contexts; standard punctuation elsewhere is fine.
