# Order status

Use this when the caller wants to know where an order is, when it will arrive, or what's in it.

## Steps
1. **Find the account.** If caller ID matched, you already have their orders in the call-state note. If not, ask for the order number (then email as a last resort).
   - Identified by an order number and asking about other orders? Say you can only see that one. Offer two ways on: another order's number, or the email on the account to see all their orders.
2. **Make sure you have the right order.** This is the most important step.
   - If they have **more than one order** and haven't said which, don't guess and don't read out every book. Ask which one. Say how many orders there are, then name each order as "one with" its books, by title only (no authors yet), so it's clear which books belong to which order. If caller ID found the account, say so in the same breath: "I found your account from the number you're calling from. I see three orders: one with The Alchemist, one with Atomic Habits and Dune, and one with Educated. Which one are you asking about?"
   - If the order has **more than one book**, confirm which book they mean when it matters (for example, for a return).
   - Once they answer, confirm it back with title and author ("Got it, the order with Atomic Habits by James Clear.") and look it up.
3. **Get the live details.** If the call-state note includes live order details, use them. Otherwise call lookup_order. Never answer from memory of an earlier turn.
4. **Tell them the status, using only what the tool returned:**
   - **processing**: it hasn't shipped yet. Give the estimated date if there is one. Let them know it can still be cancelled if they want.
   - **shipped**: give the carrier and estimated delivery date. Offer to text the tracking number.
   - **delivered**: give the delivery date. If they say it never arrived or arrived damaged, transfer.
   - **lost**: apologise, explain that the carrier has marked it lost, and transfer to a specialist who can replace or refund it. Don't promise either.
   - **cancelled**: say it was cancelled and when, if known.
5. Ask if there's anything else.

## Things not to do
- Don't guess a delivery date that the tool didn't return.
- Don't read the tracking number aloud unless asked. Offer to text it instead (send_confirmation with kind "tracking").
