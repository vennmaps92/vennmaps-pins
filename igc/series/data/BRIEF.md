# VennMaps carousel research brief

VennMaps sells state geology / river / vintage wall maps. We are making two Instagram carousel series for all 48 contiguous states. Your job is the FACTS, written as short, punchy, accurate copy for a general audience. Accuracy matters more than flair: every number, age, place and claim must be something you are confident is true; verify anything you're unsure of with WebSearch. If you can't verify something, leave it out or pick a different fact. Plain English, no jargon without explanation. American spelling. Use the en dash only in ranges; no emoji.

Write ONLY valid JSON (UTF-8) files to the paths given in your task. Do not write anywhere else.

## A. "Rock Layers" (one file per state: data/layers/<ST>.json)

Concept: "Dig down through <State>": the cover shows a stylised drill core; then one slide per layer from YOUNGEST (top) to OLDEST (bottom); each slide names the layer, its age, a hook, what it was, a fun bonus fact, and 1–3 map pins where you can see it in that state.

Pick 5 or 6 real, named rock units (formations/groups/well-known rock bodies) that are genuinely part of that state's geology and ideally famous or visible somewhere notable in the state (parks, landmarks, quarries, fossil sites, building stone, waterfalls, caves, coal/salt/oil). Spread them across geologic time from the surface/young to the oldest rock in the state (the last one may be "the basement" granite/gneiss etc. if known; for coastal-plain states it can be the oldest rock found in wells, but prefer things people can see). Each state's geology poster has a stratigraphic column for one area of the state; you may look at `all/<ST>_ig_3_full.jpg` (the column is the tall coloured bar with labels) for orientation, but your layers do not have to match it exactly.

Schema:
```json
{
 "ST": "CO", "state": "Colorado",
 "cover_sub": "Dig down through 1.8 billion years",      // <= 40 chars, the span from youngest to oldest layer
 "caption_hook": "Colorado was once a seafloor, a desert and a mountain range that vanished.",  // 1 sentence <= 110 chars, for the Instagram caption
 "layers": [
  {"name": "PIERRE SHALE",            // ALL CAPS, <= 22 chars (use THE BASEMENT / name shortened if needed)
   "age": "About 80 million years ago", // <= 30 chars; for ranges "1.1 to 1.8 billion years ago"
   "short": "80 Myr",                 // <= 8 chars, "Myr" or "Byr"
   "period": "Cretaceous",            // geologic period (or "Precambrian")
   "kind": "shale",                   // one of: shale, sand, lime, mud, gravel, granite, volcanic, meta, coal, salt, glacial
   "hook": "Colorado was the bottom of the sea",   // <= 36 chars, no final period
   "what": "A shallow seaway once split North America in two. Its mud piled up thousands of feet thick and hardened into this shale, packed with ammonites and sea-reptile bones.",   // 150–230 chars, 2 sentences
   "bonus": "It's also the swelling clay behind cracked basements along the Front Range.",  // 60–115 chars, one surprising/fun/local fact
   "pins": [["Denver", -104.99, 39.74]]   // 1–3 [label <= 18 chars, lon, lat] INSIDE the state, real places where this layer is seen/famous; pins at least 0.3 degrees apart
  }
 ],
 "sources": ["https://..."]
}
```
Reference example (approved by the owner) for Colorado: Pierre Shale (80 Myr, seaway) → Dakota Sandstone (100 Myr, Dakota Hogback, Dinosaur Ridge tracks) → Morrison Formation (150 Myr, first Stegosaurus near Morrison 1877, state fossil) → Lyons Sandstone (280 Myr, desert dunes, CU Boulder buildings) → Fountain Formation (300 Myr, Ancestral Rockies, Red Rocks/Flatirons/Garden of the Gods) → The Basement (1.1–1.8 Byr, Pikes Peak granite, Great Unconformity at Manitou Springs).

## B. "Face-off" (one file per pair: data/faceoff/<A>-<B>.json)

Concept: "<STATE A> vs <STATE B>": 5 scored rounds about mountains, rocks, rivers, lakes, landscape (VennMaps is a map brand — keep it geographic/geologic), then a fun bonus vote, then final score. Each round needs a clear winner (higher number wins; no ties), and values must be accurate and from the same kind of source for both states. Aim for a balanced, surprising scoreline (e.g. 3–2) rather than a 5–0 rout when the facts allow; mix rounds so each state wins something if possible.

Good round ideas (pick 5 that make the best contest for the pair): highest point (ft), mean elevation (ft), oldest rock (billion/million years), number of National Parks (NPS "National Park" units only), longest river in the state, largest natural lake (sq mi), miles of coastline / Great Lakes shoreline, number of peaks over some height, total water area (sq mi), number of named waterfalls is too fuzzy — avoid fuzzy counts. Land area is allowed but boring — use only if needed.

Schema:
```json
{
 "pair": "CO-UT", "a": "CO", "b": "UT", "a_name": "Colorado", "b_name": "Utah",
 "tagline": "Neighbors. Rivals. Who has the better ground?",   // <= 46 chars
 "rounds": [
   {"t": "HIGHEST PEAK",                   // ALL CAPS <= 20 chars
    "kind": "peak",                        // peak (elevations in ft), bar (any other number), dots (small whole counts 0–8)
    "a": ["Mount Elbert", 14440, "14,440 ft"],   // [sub-label <= 24 chars, numeric value, display text <= 16 chars]
    "b": ["Kings Peak", 13528, "13,528 ft"],
    "win": "a"}                             // a or b; must be the higher value
 ],                                         // exactly 5 rounds
 "bonus": {"title": "STATE FOSSIL", "sub": "You're the judge on this one",
           "a": ["Stegosaurus", "plates, spikes, brain", "the size of a walnut"],   // [name <= 16 chars, line <= 24, line <= 24]
           "b": ["Allosaurus", "the top predator of", "the Jurassic West"],
           "mid": ["Both lived in the same", "Morrison Formation rocks,", "150 million years ago."],  // 3 lines <= 28 chars each (can be empty strings)
           "q": "Who wins the fight?",                // <= 26 chars
           "cta": "Comment “STEGO” or “ALLO”"},       // <= 32 chars
 "caption_hook": "Colorado vs Utah: peaks, rocks and parks, scored.",   // <= 90 chars
 "sources": ["https://..."]
}
```
Bonus ideas: state fossil, state rock/mineral/gem, a famous landmark each, best river, a signature natural wonder — something people will argue about in the comments.
