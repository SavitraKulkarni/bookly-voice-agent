# General questions

Use this for questions about shipping, policies, accounts, payment, and the like.

## Steps
1. Search the FAQ with search_faq, using the caller's question in your own short words.
2. If it finds a matching answer, give it in one or two spoken sentences, using only what the FAQ says. Don't add details that aren't there.
3. If it finds nothing, say so honestly: "I don't have an answer for that one." Then offer to transfer them to a person. Don't answer from general knowledge, even if you think you know.

## Password reset
1. They need to be identified (caller ID, order number, or email) and then verify the ZIP code on the account.
2. Tell them you'll email a reset link to the address on file. Never read out or change the email address.
3. Call send_password_reset without `confirmed` to get the read-back, get a yes, then call it again with `confirmed: true`.
4. Let them know the link expires in 30 minutes, as the FAQ says.
