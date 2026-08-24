# Universal safety suffixes (append to every image-ad prompt)

Every skill in the image-ad family (chatgpt-image-ad, nano-banana-image-ad, and image-ad-clone's validation round-trips) appends three always-on guard suffixes to the composed prompt before generating. They are model-agnostic: they fix rendering failures that surface across **every** modern image model when generating static social-ad creatives.

There is no script doing this automatically: **you**, the executing agent, append them to the end of the prompt. You do not need to repeat these constraints inside library entries; the entries assume the guards are appended at generation time.

---

## 1. NO_CHROME_SUFFIX: strip platform/screenshot UI

Append unless the user explicitly wants simulated platform chrome as part of the concept. Forces the output to be the **standalone ad creative** (the static image an advertiser uploads), not a screenshot of how it displays in-feed.

```
[NO PLATFORM CHROME] Render only the standalone ad creative (the static image uploaded to Meta),
not a screenshot of how it displays in-feed. Exclude: iOS device chrome (status bar, home indicator);
platform brand-row above the ad (avatar + handle + Sponsored / Saved label); post body / caption text;
link-card footer (URL + headline + button); engagement rows (likes / comments / shares counts,
Followed-by, View comments); action buttons (Like / Comment / Share / Save); comment input boxes;
platform tab/nav bars (Instagram, Facebook, Twitter); Story chrome (progress bars, story header,
swipe-up arrows). Just the standalone image.
```

**When to skip it:** rare. Only when the ad's concept requires simulated platform chrome (for example a screen-recording-style UGC ad that mimics a Reels view) and the user has agreed. The chrome then becomes part of the creative on purpose.

---

## 2. SAFE_ZONE_SUFFIX: keep text and focal subjects in the central 84%

Always on, no escape hatch. Solves the "headline clipped at the edge" failure mode.

```
[EDGE-SAFE] All text, headlines, CTAs, table headers, sign/board content, product wordmarks, and
key focal subjects must fit within the central 84% of the canvas (~8% padding from every edge).
Backgrounds and divider lines may bleed; text and focal elements may NOT touch or extend off any edge.
If a tall focal subject doesn't fit at the requested aspect ratio, scale it DOWN. Never crop a
headline, never let text run off-frame, never cut off the top/bottom of a sign, board, or product.
```

---

## 3. GLYPH_SAFETY_SUFFIX: no emoji or unicode garbage inside body-text blocks

Always on. Solves the "exactly 2 comments turned into 3" and "chat-bubble emoji becomes glyph soup" failure modes.

```
[TEXT FIDELITY] Inside body-text blocks (chat bubbles, message threads, comment text, ChatGPT
responses, dense paragraphs): plain words only. NO emoji, NO unicode glyphs, NO special characters
mid-sentence. Emoji OK in headlines and short large-text positions where the prompt explicitly calls
for them. Render the EXACT count of conversation elements the prompt specifies. Do not invent
additional comments, messages, replies, or responses.
```

---

## Why all three are on by default

- They fix actual, recurring rendering failures observed across gpt-image-2 and Nano Banana.
- The total guard text is about 1,575 characters, well below every model's prompt cap.
- None of them constrain creative choice; they only constrain what the model was not supposed to be drawing in the first place.

If a model follows a guard so literally that the layout becomes stiff, you may drop that one guard for a specific run, but say so to the user and never remove the guards from your default behavior.
