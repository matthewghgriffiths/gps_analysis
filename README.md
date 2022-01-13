# gps_analysis
A python library for analysing gps data

## Example usage
```bash
~/Source/gps_analysis$ python garmin.py -h
usage: garmin.py [-h] [-u [USER]] [-p [PASSWORD]] [-a [ACTIVITY]] [--min-distance [MIN_DISTANCE]]
                 [--max-distance [MAX_DISTANCE]] [--start-date START_DATE] [--end-date END_DATE]
                 [n] [outfile]

Analyse recent gps data

positional arguments:
  n                     maximum number of activities to load
  outfile               path of output excel spreadsheet

optional arguments:
  -h, --help            show this help message and exit
  -u [USER], --user [USER], --email [USER]
                        Email address to use
  -p [PASSWORD], --password [PASSWORD]
                        Password
  -a [ACTIVITY], --activity [ACTIVITY]
                        activity type, options: rowing, cycling, running
  --min-distance [MIN_DISTANCE]
                        minimum distance of activity (in km)
  --max-distance [MAX_DISTANCE]
                        maximum distance of activity (in km)
  --start-date START_DATE
                        start date to search for activities from in YYYY-MM-DD format
  --end-date END_DATE   start date to search for activities from in YYYY-MM-DD format
```
