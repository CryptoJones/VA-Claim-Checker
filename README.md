# VA-Claim-Checker
Checks the status of a VA Claim for update with today's date and emails you if it finds one.

If the requests library isn't found you need to run 'pip install requests'

NOTE: The VA's Cookie Lifetime is set to 12 hours. You will need to repopulate the cookie data in the program every twelve hours.

NOTE2: If your claimed moved to the next step today and you want it to run again tommorow, you need to change the value in "results.txt" from "1" to "0"

NOTE3: Everything is now logged to "log.txt" instead of writing to the console

How to set cookie data. 

1: Install Chrome Extension Cookie Viewer from here: https://chromewebstore.google.com/detail/cookie-viewer/dedhcncdjkmjpebfohadfeeaopiponca

2: Log into your VA Claims site here: https://www.va.gov/track-claims/your-claims/

3: Open a new tab to: https://api.va.gov/v0/benefits_claims/

4: Click on the Cookie Viewer Chrome Extension and copy the new cookie values into the program's variables

