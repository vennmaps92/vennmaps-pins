# make_video_pins.py - one Pinterest VIDEO pin per Etsy listing, written to new_pins\video_pins.csv
# (then run plan_weekly.py to date them and fold them into the Sunday upload files).
# The 720p videos must already be on GitHub (vennmaps92/vennmaps-pins, folder videos/).
import os, csv, json
D = r"D:\States Project\etsy_listings"; P = r"D:\States Project\pintrest"
BASE = "https://raw.githubusercontent.com/vennmaps92/vennmaps-pins/main/videos/"
names = {}
for f in ("listings_batch1.csv", "listings_batch2.csv"):
    for r in csv.DictReader(open(os.path.join(D, f), encoding="utf-8-sig")): names[r["state"]] = r["state_name"]
pm = json.load(open(os.path.join(D, "detail_photos", "printful_map.json")))
INFO = {
 "vintage": ("Vintage State Map", "Vintage State Maps", "_vintage",
   "Watch this antique-style map of {n} come together in QGIS, layer by layer: counties, rivers, railroads, then old-atlas lettering. "
   "Designed in Denver by a GIS mapmaker and printed on archival matte paper. 12x18 and 24x36 prints."),
 "legend": ("Geology Map", "Geology Maps of US States", "_geology_legend",
   "Watch a geologic map of {n} being built in QGIS from USGS data: shaded relief, every rock unit, then faults. "
   "Made by a Denver geoscientist. A gift for geologists, rockhounds and {n} lovers. 12x18 and 24x36 prints."),
 "full": ("Geology Map & Strat Column", "Geology Maps of US States", "_geology_strat_column",
   "Watch a geologic map of {n} being built in QGIS from USGS data, finished with a stratigraphic column of the state's rock record. "
   "Made by a Denver geoscientist. A gift for geologists and rockhounds. 12x18 and 24x36 prints."),
 "hydro": ("River Map", "Watershed & River Maps", "_watershed",
   "Watch every river and stream in {n} flow onto shaded relief in QGIS, from USGS hydrography data. "
   "Minimalist blue map wall art by a Denver geoscientist. 12x18 and 24x36 prints."),
}
rows = []
for lid, fn in pm.items():
    st = fn[:2]; n = names.get(st, st)
    se = "vintage" if "_vintage" in fn else "hydro" if "_hydro" in fn else "legend" if "_legend" in fn else "full"
    label, board, suf, desc = INFO[se]
    rows.append({"Title": ("%s %s | Watch It Being Made in QGIS" % (n, label))[:100],
                 "Media URL": BASE + st + suf + "_video.mp4", "Pinterest board": board,
                 "Thumbnail": "7",                     # cover frame: 7 s in, the finished poster
                 "Description": desc.format(n=n)[:500], "Link": "https://www.etsy.com/listing/%s" % lid,
                 "Publish date": "", "Keywords": "%s map, map making, QGIS, %s, map wall art" % (n, label.lower())})
os.makedirs(os.path.join(P, "new_pins"), exist_ok=True)
import random; random.seed(5); random.shuffle(rows)    # mix states and series
with open(os.path.join(P, "new_pins", "video_pins.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(len(rows), "video pins written")
