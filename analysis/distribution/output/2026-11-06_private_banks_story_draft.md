# Private banks, Sep 2026: the story draft

> Drafted 2026-11-06 by Claude for the user to rewrite. Replaces the table-per-measure scorecard in this
> folder (its PDF and post.md are the old version); nothing is rebuilt yet. Data month: Sep 2026.
> "Growth" is always year on year. Value = rupee value of credit card spends at shops (POS). Swipes = number
> of those transactions. Share = share of all banks.

## The post

Private banks run most of India's credit card spending at shops. And in September, that spending almost stopped growing.

They hold 72.7% of the value. Their growth fell from 4.2% in August to just 1.4%. The market grew 7.2%.

But that 1.4% hides four very different stories.

1. The two giants are shrinking.

HDFC Bank fell 6.7%, after growing 0.9% in August. ICICI fell 9.2%. HDFC has a real excuse: it was growing 36.1% a year ago. And its swipes are still up 17.7%, so people are using the cards, just for less money.

ICICI has less of an excuse. It grew 8.8% a year ago, and its swipes are down too. Since Jan 2024, its share of swipes has gone from 11.2% to 5.2%.

2. Axis is the one big bank still moving.

Value up 15.7%, faster than August's 11.6%, and that's on top of 46.5% growth last year. Swipes up 29.0%.

3. The challengers are growing fast, each in its own way.

Yes Bank +41.6%, and it was already growing 42.0% a year ago. Federal Bank +40.7%, with cards in force up 75.0%. IDFC First +26.8%. Kotak +35.8% with cards up only 7.3%, though Kotak's number comes off a weak year (−1.3%).

4. Two banks are falling behind.

IndusInd is down 42.8%, after falling 23.0% a year ago. Its share has gone from 3.6% to 2.2% since Jan 2024. RBL's value is up just 3.9%, with swipes down 8.4%.

Add it up, and the falls at HDFC, ICICI and IndusInd cancelled most of what the growers added.

Now the twist: even so, this wasn't where the growth went. Public sector banks took 71.0% of the market's growth, up from 51.0% in August. Private banks took 14.7%. SBI alone grew 25.2%, with swipes flat (−0.3%).

So who's actually winning cards in India? If you work on cards at one of these banks, what am I missing?

@HDFC Bank @ICICI Bank @Axis Bank @Yes Bank @Federal Bank @IDFC FIRST Bank @Kotak Mahindra Bank @IndusInd Bank @RBL Bank

#CreditCards #PrivateBanks #DigitalPayments

Data: RBI ATM, POS and card statistics, Sep 2026 · indiacreditlens.com

## The slides

**1. Hook.** Private banks' card spending almost stopped growing
- Big: 72.7% of the value · +1.4% growth
- Line: The market grew 7.2%.
- Band: In a month, their yearly growth went from 4.2% to 1.4%.

**2. Puzzle.** So how are some of them growing 40%?
- Big: Yes Bank +41.6% vs IndusInd −42.8%
- Line: Inside that 1.4%, nine banks are living four different stories.
- Small table: the nine banks, share and growth only, grouped into the next four slides.

**3. The giants shrink.** HDFC and ICICI: the biggest names, going backwards
- Big: HDFC −6.7% · ICICI −9.2%
- Chart, the only one in the set: value share since Jan 2024 for HDFC, ICICI, Axis. HDFC's one-month drop circled.
- Line: HDFC has a high base (+36.1% a year ago), and it's back near where it began (26.9% → 26.5%). ICICI has a lower one (+8.8%).
- Band: In a month, yearly growth went from 0.9% to −6.7% at HDFC, −5.1% to −9.2% at ICICI.

**4. The one still moving.** Axis: a big bank that's still growing
- Big: +15.7% value · +29.0% swipes
- Line: On top of +46.5% a year ago. Its UPI QR codes also went from 13.05 to 19.37 crore in one month. A real push, or a reporting change?
- Band: In a month, yearly growth went from 11.6% to 15.7%.

**5. The challengers.** Small banks, fast growth, four different ways
- Table: Yes Bank +41.6% (and +42.0% a year ago) · Federal Bank +40.7% (cards +75.0%) · Kotak +35.8% (cards +7.3%, weak base) · IDFC First +26.8% (cards +23.7%)
- Band: In a month, all four eased a little: Yes 42.3% to 41.6%, Federal 44.4% to 40.7%, Kotak 39.4% to 35.8%, IDFC First 30.2% to 26.8%.

**6. Falling behind.** Two banks going the other way
- Big: IndusInd −42.8% · RBL +3.9%
- Line: IndusInd's share went from 3.6% to 2.2% since Jan 2024, RBL's from 5.8% to 3.2%. RBL's swipes are down 8.4%.
- Band: In a month, IndusInd's yearly fall eased from −47.7% to −42.8%. RBL held, 3.7% to 3.9%.

**7. The twist.** But the growth didn't go to private banks anyway
- Big: Public banks 71.0% of the growth vs private banks 14.7%
- Line: SBI grew 25.2%, with swipes flat at −0.3%.
- Band: In a month, public banks' share of the growth went from 51.0% to 71.0%.
- Ask: So who's actually winning cards in India? If you work on cards at one of these banks, what am I missing?

## Where each number comes from

Sidecars are in `web/public/data/`. Series readings are by month: Aug 26 = −2, Sep 25 = −13, Jan 24 = first.

| Numbers | Source |
|---|---|
| Private 72.7%, growth 4.2% → 1.4%, 35.6% → 14.7% of growth; Public 51.0% → 71.0%; market 7.2% | `atm_pos_table.json` › `cc-pos-txn-val-category` |
| Value growth by bank, Aug → Sep and a year ago; value share now and Jan 24 | `atm_pos_banks/cc-pos-txn-val-banks.json` |
| Swipes growth by bank; ICICI swipe share 11.2% → 5.2% | `atm_pos_banks/cc-pos-txn-vol-banks.json` |
| Cards in force growth (Federal, Kotak, IDFC First) | `atm_pos_banks/credit-cards-banks.json` |
| Axis UPI QR 13.05 → 19.37 crore | `atm_pos_banks/upi-qr-banks.json` |

## Traps

- **"Cancelled most of what the growers added" is my arithmetic, not a stored number**, so the post gives no figure. Backing out last year's value from size and growth: HDFC, ICICI and IndusInd lost about ₹3,600 Cr, and Axis, Yes, Kotak, IDFC First, Federal and RBL added about ₹4,400 Cr. That leaves about ₹800 Cr, close to the private total's +1.4%. Remove the line if you want only stored facts.
- **HDFC's Dec 2025 drop** (30.8% → 26.6%) came as Axis, ICICI and SBI all gained share that month. It looks like more than demand, but we have no source, so the post doesn't mention a cause.
- **Base effects cut both ways.** HDFC and Axis have high bases. Kotak's comes off −1.3% and its cards off −14.2%, RBL's off −6.2%. The post says so for HDFC, Axis and Kotak; RBL's is left out.
- **Yes Bank is the cleanest challenger:** +42.0% a year ago and +41.6% now, so no base excuse.
- **Federal's cards** are in force, not new issues, and the base is small (28.18 lakh cards).
- **Groupings** (giants, challengers, falling behind) are editorial, not stored categories.
- **Online value is left out on purpose:** HDFC's share jumped in Aug and Sep, and the market's fall sits on a large Sep 2025.
- **Tagging:** IndusInd and RBL's teams will read slide 6. It states numbers and no cause. Your call.
