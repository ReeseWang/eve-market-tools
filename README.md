# eve-market-tools
Some command-line scripts which analyse EVE Online in-game market data and find the most profitable actions.

## Usage:
 1. Login at https://developers.eveonline.com/ and create an application to get your developer client ID and secret key. 
 You may have to have used a payment method other than PLEX with CCP to create an application. I will consider adding an option
 to not to use authentication, but in that case the functionality will be limited, such as not able to know which solar system an 
 order is located in and whether you have access to it if it's in a player structure (citadel), not able to add waypoint and open market 
 detail window automatically.
 2. Clone or download the repository.
 3. Create `secret.py` in the project folder with following content:
 ```python
 clientID = 'your-client-id'
 secretKey = 'your-secret-key'
 
 # Make your application callback URL setting on the dev site identical to this, you can change both if you want.
 callbackUrl = 'https://localhost/copy-following-string'
 scopes = ['esi-ui.write_waypoint.v1',
           'esi-markets.read_character_orders.v1',
           'esi-location.read_location.v1',
           'esi-ui.open_window.v1',
           'esi-location.read_online.v1',
           'esi-universe.read_structures.v1'
           ]
 ```
 4. Run `./download-sde-database-sqlite.sh` to download a SQLite convertion of EVE static data export.
 5. Run `./find-haul-route.sh`. You will be asked to copy-paste something to and from your browser. Then just follow the prompt. 
 Current implementation is pretty stupid. You can't expect too much about a project that was born yestoday after all. 
 But it will improve over time.
  
