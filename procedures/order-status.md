# Order status

Use this when the caller wants to know where an order is, when it will arrive, or what's in it.

## Steps
1. **Find the account.** If caller ID matched, you already have their orders in the call-state note. If not, ask for the order number (then email as a last resort).
2. **Make sure you have the right order.** This is the most important step.
   - If they have **more than one order** and haven't said which, don't guess and don't read out every order. Ask which one, naming each by its book: "I see a few recent orders: one with Klara and the Sun by Kazuo Ishiguro, one with The Overstory by Richard Powers, and an older one with Educated by Tara Westover. Which one are you asking about?"
   - If the order has **more than one book**, confirm which book they mean when it matters (for example, for a return).
   - Once they answer, confirm it back ("Got it, the order with The Overstory by Richard Powers.") and look it up.
3. **Look up the order** with lookup_order. Always check live data, even if you saw the order in the summary.
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
