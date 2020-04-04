import datetime

def main():
    startdate = datetime.date(2019, 8, 1)
    enddate = datetime.date(2020, 4, 30)

    names_of_days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",   
    ]

    d = startdate
    while d <= enddate:
        dow = d.weekday()
        dow_name = names_of_days[dow]

        if dow_name == "Sunday":
            print()
            print('Time for another week')  

        print("date is {date}".format(date=d))
        print("Day of week is {dow}.".format(dow=dow_name))
        d = d + datetime.timedelta(1)

if __name__ == "__main__":
    main()
