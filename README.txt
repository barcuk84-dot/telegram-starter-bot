FINDTAG + USERNAME HUNTER (integrated)

1) Install Python 3.12.
2) Open CMD in this folder.
3) Run: py -3.12 -m pip install -r requirements.txt
4) Copy .env.example to .env.
5) Fill BOT_TOKEN, ADMIN_IDS, API_ID and API_HASH. Never share .env.
6) Run: py -3.12 main.py
7) On first start, Telethon asks in the terminal for the phone number and login code of the Telegram account.
   The authorization is stored in findtag_session.session. Do not send that file to anyone.

The bot offers both sources: admin-managed SQLite database and on-demand live MTProto checks.
The live scanner generates candidates and calls Telegram CheckUsernameRequest. It skips occupied, invalid, and Fragment/collectible-reserved usernames.

Important: This checks whether Telegram currently accepts the username for assignment to the logged-in account. It does not transfer ownership to a buyer. The estimated beauty/liquidity/TON values are heuristic only, not Fragment market quotes.

Use a dedicated session name (findtag_session). Do not run two processes that open the same .session file at the same time. The separate desktop Username Hunter may continue using its own `session` file.
