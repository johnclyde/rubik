import datetime
from .dumb_renderer import DumbRenderer

names_of_days = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",     
]


def main(
    renderer,
    startdate,
    enddate,
):

    week = []

    d = startdate
    while d <= enddate:
        dow = d.weekday()
        dow_name = names_of_days[dow]

        if dow_name == "Sunday":
            renderer.render_week(week)
            week = []

        week.append(d) 
        d = d + datetime.timedelta(1)

    renderer.render_week(week)


if __name__ == "__main__":
    renderer = DumbRenderer()
    startdate = datetime.date(2019, 8, 1)
    enddate = datetime.date(2020, 4, 30)

    main(
        renderer=renderer,
        startdate=startdate,
        enddate=enddate, 
    )
