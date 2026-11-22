# Admin and participant accounts

The home page is now a login/activation page. Administrators create benchmarks
and issue three invitations. Participants activate their own invitation, choose
a password, sign in, and submit directly to their assigned MPyC party. No salary
is posted to the account API. Results remain in the existing admin dashboard.

## Setup

Configure the existing private environment and PostgreSQL connection, then run:

```sh
python -m alembic upgrade head
python -m scripts.create_admin
```

The administrator creation command prompts for the username and password; it
does not accept passwords on the command line. Do not commit the environment,
database, or credentials. The administrator must be provisioned on the backend
host, not through an unauthenticated public signup endpoint.

## Demonstration

1. Sign in as administrator and create a 30-minute benchmark.
2. Enter three unique lowercase usernames, one per party, and issue invitations.
3. Copy each invitation and privately give it to the intended participant.
4. In three independent browser profiles/devices, open the home page, select
   “I have an invitation”, and activate each account with its own password.
5. Sign in and submit the three inputs. The administrator sees receipt status,
   never individual inputs. Start computation once all three have submitted.
6. Sign out when finished. Login sessions expire after one hour and are stored
   only in browser memory; refreshing the page requires signing in again.

These demonstration participant accounts are assigned to one benchmark. Use
new usernames for subsequent benchmarks. Invitations expire with the benchmark;
password reset, invitation reissue, and reassigning accounts are not yet supplied.

Passwords use salted scrypt. Invitation and login tokens are stored only as
SHA-256 hashes; activation consumes the invitation. Five failed attempts lock
an account for 15 minutes. Deploy the API only through HTTPS. The legacy admin
token and founder capability endpoints remain available for operational smoke
tests; account-based session creation omits raw founder capabilities from the
response. Hosts/operators remain trusted and can manage server configuration.

Three processes on one host demonstrate real MPC and separate participation,
not independence between hosting administrators. Free-cloud packaging and a
live public deployment are separate steps; this change does not claim either.
