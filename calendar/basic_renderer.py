class BasicRenderer(object):

    names_of_days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",     
    ]

    def render_week(self, week):
        print()
        displays = []
        for d in week:
            dow = d.weekday()
            dow_name = self.names_of_days[dow]
            displays.append('{date.day:>2}'.format(date=d))
        print(' '.join(displays))        
                    
            
