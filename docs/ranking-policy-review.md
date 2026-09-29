# Ranking policy: tradeoff to test

Keep the existing explainable, deterministic algorithm unchanged for now.
Urgency tiers take precedence over scores. Consequently, an unstarted task whose
planned start passed five minutes ago and whose deadline is four days away ranks
above an unstarted task due in twelve hours whose planned start is still ahead,
even when the latter has a higher score.

This is current behavior, not a validated student preference. Before changing it,
show students both tasks without revealing the recommendation, ask which they
would start and why, then show the existing explanation and ask whether it fits
their expectations. Include different effort estimates and degrees of lateness.
Record disagreements and reasons; do not infer a preference from the score alone.

Revisit tier precedence only after reviewing that feedback. Avoid additional
weights or complexity without evidence. A regression test in
`tests/test_suggestion_service.py` records this exact case and checks that input
order does not change the result. Update that test deliberately if policy changes.
