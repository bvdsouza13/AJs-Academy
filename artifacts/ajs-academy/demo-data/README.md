# Fictional financial fixtures

These two CSVs are the user-supplied scrambled demo files, not the original
family account exports. They are bundled so financial demo mode works after
reloads and does not depend on temporary chat-attachment paths.

- `college.csv`: fictional 529 activity and a fictional holding snapshot.
- `custody.csv`: fictional custodial activity, not a holdings statement.

The display parser removes account and CUSIP identifiers. Neither file is
parent-reviewed statement evidence. The app must not infer an account balance,
personal return, or verified holdings from custodial activity.

Demo mode is controlled by a parent in Financial reports. It overlays only the
two financial displays; original saved exports, statement evidence, balances,
and assumptions remain unchanged. Financial imports and saves are unavailable
while demo mode is active. Diary, rewards, media, and other saved family records
are not demo data and are not replaced or anonymized by this feature.
