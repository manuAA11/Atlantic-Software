# Authorization handoff encryption

TweetNaCl.js 1.0.3, upstream commit e6141a20553498697e9e7d92fbc4517994caff52. Source: https://github.com/dchest/tweetnacl-js. Public domain; see UNLICENSE.

Used only to encrypt the official one-session Wrangler device verification link for the authorized deployment operator. The repository contains the recipient public key only. OAuth credentials stay on the ephemeral CI runner and the workflow logs out after deployment.
