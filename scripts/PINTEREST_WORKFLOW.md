# VennMaps Pinterest workflow

Pins are hosted on GitHub (`vennmaps92/vennmaps-pins`, public) and scheduled through Pinterest's free bulk uploader:
https://www.pinterest.com/settings/bulk-create-pins

Pinterest's limits: about 100 pins scheduled at once, nothing more than about 30 days ahead, and no two pins in one file can share a title (a duplicate makes the whole file fail). Because of that, pins go up in weekly batches.

## Every Sunday (about 2 minutes)
1. Upload this Sunday's file, `weekly_YYYY-MM-DD_upload.csv`, on the bulk page above.
2. Record it as uploaded (run from this folder):
   `python plan_weekly.py --uploaded weekly_YYYY-MM-DD_upload.csv`
   This moves the file to `_already_uploaded\` and logs its dates in `uploaded_dates.json`, which the planner uses to count the 100-pin cap.

## Adding new pins later (new states, new styles)
1. **Image pins:** run `python make_pins.py ST ST ...` to make the images in `pins\` and a CSV of rows.
   **Video pins:** run `python encode_videos_for_pinterest.py` to put 720p copies in `videos\`, then `python make_video_pins.py`.
2. Push the new images or videos to GitHub, in the `pins/` or `videos/` folder of the repo. Pinterest reads them from `https://raw.githubusercontent.com/vennmaps92/vennmaps-pins/main/...`.
3. Put the new rows (no publish date needed) in a CSV in `new_pins\`.
4. Run `python plan_weekly.py`. It dates the new pins three a day, in their own time slots, starting the day after the next Sunday. It then rebuilds every `weekly_*_upload.csv` within the caps and moves the `new_pins` files to `_already_uploaded\added_*`.

Use the OSGeo4W Python, or any Python 3; the planner needs only the standard library.

## Files
| File | What it is |
|---|---|
| `weekly_*_upload.csv` | Still to upload, one per Sunday (rebuilt by `plan_weekly.py`) |
| `new_pins\` | Drop new pin rows here, then run `plan_weekly.py` |
| `_already_uploaded\` | Files already on Pinterest, plus `uploaded_dates.json` |
| `pins\` | Image pins (1000x1500), mirrored to GitHub `pins/` |
| `videos\` | 720p video pins, mirrored to GitHub `videos/` |
| `make_pins.py` | Builds image pins plus rows |
| `encode_videos_for_pinterest.py` | Makes 720p copies of the Etsy listing videos |
| `make_video_pins.py` | Builds one video-pin row per Etsy listing |
| `plan_weekly.py` | Dates the pins and rebuilds the Sunday files |

## CSV columns
Title, Media URL, Pinterest board, Thumbnail, Description, Link, Publish date (UTC, ISO), Keywords.
For video pins, Thumbnail is the second of the video used as the cover (7 = the finished poster).

Boards: Geology Maps of US States, Vintage State Maps, Watershed & River Maps.
