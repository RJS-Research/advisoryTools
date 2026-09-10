# The Investment Office Decision

subtitle: Where to sit on the outsource to insource spectrum
footer: ILLUSTRATIVE FIXTURE, SYNTHETIC NUMBERS, NOT CLIENT DATA

<!--
  Bake-off fixture for the two renderers. Client neutral by construction.

  EVERY NUMBER BELOW IS INVENTED to exercise the chart paths. None of it is
  researched, sourced, or attached to any engagement. Real figures arrive from
  the spikes in _prompts/4a..4d and are never authored here. See the project
  rule: never guess a financial figure.

  Dialect, deliberately small so both renderers can implement it identically:
    # Title            deck title slide (with optional subtitle:/footer: lines)
    ## Slide title     starts a new content slide
    - bullet           body bullet, one level
    ```chart {...}```  a NATIVE PowerPoint chart, JSON spec
    > note             speaker note for the current slide
-->

## What has to be decided

- How much of the investment function the institution owns
- How it prefers to pay for the rest, as a percentage or as a fixed cost
- Who holds the decision at each point, and at what forum
- What each choice forecloses, which is the part a menu hides

> The decision inventory is the real deliverable of this stage. The spectrum is how
> we make the inventory legible, not the answer itself.

## The spectrum, and what each position covers

- Position 1, full discretionary outsource: provider decides inside an agreed policy
- Position 2, non-discretionary advisory: committee decides on provider recommendations
- Position 3, split mandate: divided by sleeve, commonly liquid against illiquid
- Position 4, lean team plus access vehicle: the position most often missing from the menu
- Position 5, full internal office: institution owns front, middle and back

```chart
{
  "type": "bar",
  "title": "Activity coverage by position (illustrative, count of functions owned internally)",
  "categories": ["1 Outsource", "2 Advisory", "3 Split", "4 Lean + access", "5 Internal"],
  "series": [
    {"name": "Front office", "values": [0, 1, 3, 5, 7]},
    {"name": "Middle office", "values": [0, 1, 2, 4, 6]},
    {"name": "Back office", "values": [0, 0, 1, 2, 7]}
  ]
}
```

> Back office effort scales with the number of relationships, not with AUM. That is why
> illiquid tilt drives insourcing cost far more than portfolio size does.

## Why the pricing model is the real question

- Outsourced positions price as basis points on AUM, so cost rises with the portfolio
- Insourced positions price in fixed dollars, so cost per dollar managed falls as it grows
- That difference is operating leverage, and it is the whole economic case for moving right
- The crossover is a number, not a direction, and it has to be stated as one

```chart
{
  "type": "line",
  "title": "Cost by AUM: bps on AUM against fixed dollars (ILLUSTRATIVE, synthetic)",
  "categories": ["$250mn", "$500mn", "$750mn", "$1.0bn", "$1.5bn", "$2.0bn"],
  "series": [
    {"name": "Outsourced (bps on AUM)", "values": [1.25, 2.50, 3.75, 5.00, 7.50, 10.00]},
    {"name": "Insourced (fixed dollars)", "values": [3.60, 3.60, 4.90, 4.90, 6.20, 6.20]}
  ]
}
```

> Fixed costs are only fixed until they break. Headcount steps in lumps, so the insourced
> line is a staircase, and the crossover should be drawn as one rather than as a smooth curve.

## What the crossover does not settle

- Cost is not the only axis; governance capacity and access move independently
- The transition itself has a cost, in fees, in staff time, and in the gap between arrangements
- Insourcing converts a fee into an employment relationship, moving key person risk in-house
- For an institution with a live succession question that is the point, not a footnote

> Say these on the same slide as the crossover. Without them the argument overstates itself,
> which is the fastest way to lose a committee that already suspects the answer is predetermined.
