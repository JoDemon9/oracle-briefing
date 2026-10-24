DEC-024: the approved source upgrade uses immutable assets/snapshot-objects/<sha>.<ext> for new snapshots. Verify their exact bytes against reviewed source assets; preserve legacy snapshot directories, old URLs, Wire and original times. Repository prompts do not update live tasks.

# Oracle portal — Λειτουργία

Η μοναδική κανονική πολιτική βρίσκεται στο [Claude-Briefing/BRIEFING_RUNTIME.md](https://github.com/JoDemon9/Claude-Briefing/blob/main/BRIEFING_RUNTIME.md), DEC-023. Τα πλήρη prompts βρίσκονται στα [Morning](https://github.com/JoDemon9/Claude-Briefing/blob/main/prompts/morning.md), [Midday](https://github.com/JoDemon9/Claude-Briefing/blob/main/prompts/midday.md), [Evening](https://github.com/JoDemon9/Claude-Briefing/blob/main/prompts/evening.md). Pending PR δεν ισοδυναμεί με εγκατεστημένο main.

Το Oracle αποθηκεύει την πλήρη ημερήσια εφημερίδα και τον ανεξάρτητο Wire· δεν παράγει εκδόσεις. Το sync γίνεται από τον διατηρούμενο resumable publisher, αφού επαληθευτεί το συγκεκριμένο source release, και ακολουθεί πραγματική επαλήθευση του Oracle. Διατηρούνται παράλληλα Wire commits, ιστορικά URLs, αρχικές ώρες και τελευταία καλή δημοσίευση. Δεν εξάγονται ιδιωτικές σημειώσεις ή caches.

Η νεότερη οδηγία του χρήστη απαιτεί συνέχιση με ειλικρινή μερική διαθεσιμότητα. Προσωρινή απουσία φωτογραφίας/τιμής/αθλητικής πηγής περιορίζει το στοιχείο και δεν ρίχνει ολόκληρη την έκδοση. Μη τεκμηριωμένο γεγονός δεν παρουσιάζεται ως γεγονός. Πραγματικά τεχνικά/integrity σφάλματα σταματούν την προώθηση και διατηρούν την τελευταία καλή έκδοση.

Οι υπάρχουσες ώρες 07:30/13:30/19:30 Europe/Athens, τα settings των tasks και το πρόγραμμα Wire δεν αλλάζουν. Git edits και πραγματικά task settings ελέγχονται χωριστά. Καθημερινά ισχύουν content/preview/integrity με τις δύο συμφωνημένες διαμορφώσεις browser· maintenance units προστίθενται σε αλλαγές κώδικα, ενώ πλήρες ιστορικό browser audit εκτελείται μόνο όταν ζητηθεί. Δεν γίνεται αυτόματο merge PR.
