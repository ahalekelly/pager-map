# Bay Area transmitters near the 902–928 MHz ISM band

`index.html` maps active FCC site-licensed transmitters between 900 and 932 MHz around the SF Bay Area, the range that threatens 902–928 MHz ISM receivers such as LoRa mesh nodes: Location and Monitoring Service tag readers inside the band, 929–932 MHz paging just above it, and 928 MHz Part 101 SCADA remotes. Each marker is one frequency at one site, colored by category, with area proportional to its licensed ERP. Click a marker for its licenses, power, and antenna height.

To rebuild from the latest weekly ULS dumps:

```bash
cd uls && for f in l_paging l_LMcomm l_micro; do curl -sSfO https://data.fcc.gov/download/pub/uls/complete/$f.zip && mkdir -p $f && unzip -o -q $f.zip -d $f; done && cd ..
uv run build.py uls
```

Only fixed sites with coordinates appear. Area licenses are missing, including 930–931 MHz narrowband PCS paging, mobile radios, and some toll readers.
