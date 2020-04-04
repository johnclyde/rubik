import datetime

startdate = datetime.date(2019, 8, 1)
enddate = datetime.date(2020, 4, 30)

d = startdate
while d <= enddate:
    print("date is {date}".format(date=d))
    print("Day of week is {dow}.".format(dow=d.weekday()))
    d = d + datetime.timedelta(1)
