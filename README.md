# gps_analysis
A python library for analysing gps data

## Example usage
```
$ gpx --help
usage: gpx [-h] [-o [OUT_FILE]] [-l-log LOG] [gpx_file [gpx_file ...]]

Analyse gpx data files

positional arguments:
  gpx_file              gpx files to process, accepts globs, e.g. activity_*.gpx, default='*.gpx'

optional arguments:
  -h, --help            show this help message and exit
  -o [OUT_FILE], --out-file [OUT_FILE]
                        path to excel spreadsheet to save results, default='gpx_data.xlsx'
  -l-log LOG, --log LOG
                        Provide logging level. Example --log debug', default='warning'

$ garmin --help
usage: garmin [-h] [-u [USER]] [-p [PASSWORD]] [-a [ACTIVITY]] [--min-distance [MIN_DISTANCE]]
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
