from datetime import datetime
import pytz
  
print("current time: ", datetime.now(pytz.timezone('Europe/Rome')).strftime('%Y-%m-%d %H:%M:%S %Z %z'))
  

