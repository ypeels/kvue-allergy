'''
Get today's allergy forecast and email it to myself.

First version: 
Start at 11:54. How fast can I whip this up?
Finished and tested at 12:16

But that was just a real fast wget, regex, and spam. 
'''
import datetime
import HTMLParser
import re
import requests # stupid unscrapable keepandshare.com
import time # sleep
import utility

ENDL = '<br/>\n'
PORTAL_URL = 'http://www.kvue.com/weather/allergy-forecast/'
PREFIX = 'allergy' # TODO: bootstrap from __file__ - meh
LOG_FILE = PREFIX + '.log'
WAITFOR = 900 # seconds to wait before polling keepandshare.com
WAIT_UNTIL_HOUR = 12 # stop polling after noon

MESSAGE_TEMPLATE = '''
<html><body>
{summary}
<a href="{portal}">{images}</a>
{maintext}{endl}
{endl}
Calendar (mobile): http://www.keepandshare.com/calendar/mobile.php?i=1940971{endl}
Calendar (desktop): http://www.keepandshare.com/calendar/show.php?i=1940971{endl}
KVUE website: {portal}{endl}
Latest forecast: http://www.kvue.com/weather/allergy-forecast/allergy-report/44055429{endl}
</body></html>
'''

mailing_list = [
	('name@example.com', 'remote_image')
    ]

def die(errormsg):
    utility.die(errormsg, LOG_FILE)
    
def log_error(errormsg):
    utility.log_error(errormsg, LOG_FILE)
    
def wget(url):
    return utility.wget(url, die)
    


def get_forecast_from_kvue(portal_text):
    '''get today's forecast from kvue.com - moved to function JUST in case I want to call repeatedly'''
    FAILURE_RETVAL = ''
    
    print("Getting today's allergy forecast...")
    
    forecast_matches = re.findall(r'href="(/weather/allergy-forecast/allergy-report/[0-9]+)"', portal_text)
    if len(forecast_matches) < 1:
        log_error('forecast regex failed')
        return FAILURE_RETVAL
        
    # Just emailing the raw html in `forecast` is way too messy
    forecast_url = 'http://www.kvue.com' + forecast_matches[0]
    forecast = wget(forecast_url)
    allergy_matches = re.findall(r'\s{3,10}<p>(.*?)</p>', forecast)
    if not allergy_matches or len(allergy_matches) < 1:
        log_error('allergy regex failed')
        return FAILURE_RETVAL
    forecast_maintext = allergy_matches[0]
    # still need to verify whether this is today's forecast.
    
    date_regex = re.compile(r'updated on (.*?)\.')
    date_matches = date_regex.findall(forecast_maintext)
    if not date_matches or len(date_matches) < 1:
        log_error('date regex failed')
        return FAILURE_RETVAL
        
    try:
        datetime_updated = datetime.datetime.strptime(date_matches[0], '%A, %B %d, %Y')
    except ValueError:
        log_error('date parsing failed: ' + date_matches[0])
        return FAILURE_RETVAL        
    
    if datetime_updated.date() != datetime.date.today():
        log_error('Warning: out of date forecast: ' + str(datetime_updated))
        forecast_maintext = forecast_maintext[date_regex.search(forecast_maintext).end()+1:]
    
    # forecast is finally verified as today's - more readable than tons of nested scaffolding?
    print(HTMLParser.HTMLParser().unescape(forecast_maintext))
    return forecast_maintext
    
    
    
def get_images_from_kvue(portal_text):
    print('Looking for images, which are more up to date than main page')
    images_html = ''
    image_matches = re.findall(r'"(http://cdn.tegna-media.com/kvue/weather/[^"]*.jpg)"', portal_text)
    for image_url in image_matches:
        images_html += '<img src="{url}" width="480px" />{endl}'.format(url=image_url, endl=ENDL)
    return images_html
    
    
    
def kvue_forecast_is_current(forecast):
    matches = re.findall(r'This allergy forecast was updated on [A-Za-z]+, ([A-Za-z]+) ([0-9])+, ([0-9]{4})\.', forecast)
    if len(matches) != 1:
        log_error("forecast date regex failed")
        return False
        
    month_str, day_str, year_str = matches[0]
    forecast_date = datetime.date(int(year_str), month_from_string(month_str), int(day_str))
    return forecast_date == datetime.date.today()
    
    
    
def month_from_string(string):
    month_map = {
        'January': 1,
        'February': 2,
        'March': 3,
        'April': 4,
        'May': 5,
        'June': 6,
        'July': 7,
        'August': 8,
        'September': 9,
        'October': 10,
        'November': 11,
        'December': 12
        }
        
    return month_map.get(string, 0)
    
    
    
def get_forecast_from_calendar():
    '''
    pull weekend forecast text directly "from" http://www.keepandshare.com/calendar/show.php?i=1940971 - calendar.js
    https://news.ycombinator.com/item?id=7066479 - i was so close - just had params as dateFrom/dateTo instead of from/to
    http://www.keepandshare.com/calendar/fns_asynch_api.php?r=getrange
    '''
    today = str(datetime.date.today())
    response = requests.post( 'http://www.keepandshare.com/calendar/fns_asynch_api.php', params={
        'i': 1940971, 'action': 'getrange', 'from': today, 'to': today} )
    try:
        #summary = response.json()['data']['dateToContent'][today]['notetext']['display_text']
        summary = response.json()['data']['dateToContent'][today]['events'][0]['text_key']
    except (ValueError, KeyError):
        summary = ''
    
    print('\nSummary from calendar:')
    print(summary)
    return summary
    
    
    
def send_email(summary, forecast_maintext, images):
    message = MESSAGE_TEMPLATE.format(
        summary=summary, maintext=forecast_maintext, portal=PORTAL_URL, images=images_html, endl=ENDL)
        
    subject = 'Allergy forecast'
        
    output_filename = PREFIX + '_email.htm'
    with open(output_filename, 'w') as output:
        output.write(message.encode('utf8'))
        
    # meh, just throw it away (don't log it) - download the full allergy calendar once a year
    # 2016-02-24: html format because they had some html-formatted text today...
    # 2016-02-26: sure, save the pictures for posterity
    for mailto, image_pref in mailing_list:
        if image_pref == 'attached_image':
            print('Sending full attached image via vbs to ' + mailto)
            utility.send_spam_vbs(output_filename, subject, mailto)
        elif image_pref == 'remote_image':
            print('Sending remote image to ' + mailto)
            utility.send_spam(message, subject, mailto, message_type='html')
        else:
            log_error('unsupported mailer {} for {}'.format(mailer, mailto))
        

        
        
        
if __name__ == '__main__':
    portal_text = wget(PORTAL_URL)  
    images_html = get_images_from_kvue(portal_text)
    forecast_maintext = get_forecast_from_kvue(portal_text)
        
    # wait for keepandshare.com to have an up-to-date forecast
    summary = get_forecast_from_calendar()
    check_calendar_again = not kvue_forecast_is_current(forecast_maintext)
    while not summary and check_calendar_again:
        log_error('Waiting {} seconds for keepandshare to update'.format(WAITFOR))
        time.sleep(WAITFOR)
        summary = get_forecast_from_calendar()
        
        if datetime.datetime.now().time().hour >= WAIT_UNTIL_HOUR:
            check_calendar_again = False

    send_email(summary, forecast_maintext, images_html)
