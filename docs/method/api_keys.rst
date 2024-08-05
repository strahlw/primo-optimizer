API Keys
========

PRIMO utilizes the `Bing Maps API <https://www.bingmapsportal.com/>`_ to extract the distance from the nearest road point for a well and the 
`US Census API <https://api.census.gov/data/key_signup.html>`_ to identify whether a well lies in a disadvantaged area. 
You will need to provide your own API keys to use these APIs by signing up at the links above.

These API Keys can be utilized by providing them in a .env file. A .env file is a text file at the root folder of the project formatted as follows::

    BING_API_KEY="My Bing maps key"
    CENSUS_KEY="My census key"


.. note::
    The .env file has extension .env and no name. If you run into errors, please confirm the file is not accidentally named .env.txt.