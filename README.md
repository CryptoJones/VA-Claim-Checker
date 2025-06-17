# VA-Claim-Checker
Checks the status of a VA Claim for update

If the requests library isn't found you need to run 'pip install requests'

NOTE: The VA's Cookie Lifetime is set to 12 hours. You will need to repopulate the cookie data in the program every twelve hours.

How to set cookie data. 

1: Install Chrome Extension Cookie Viewer from here: https://chromewebstore.google.com/detail/cookie-viewer/dedhcncdjkmjpebfohadfeeaopiponca

2: Log into your VA Claims site here: https://www.va.gov/track-claims/your-claims/

3: Open a new tab to: https://api.va.gov/v0/benefits_claims/

4: Click on the Cookie Viewer Chrome Extension and copy the new cookie values into the program's variables

