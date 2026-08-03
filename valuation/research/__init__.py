"""Research modules — signal prototypes that are NOT wired into the live panel.

Anything in here is exploratory by construction: it builds or scores a candidate dataset so
the gated IC test (CPCV / held-out) can be run on it later. Nothing here is imported by
`valuation.edge.fundamental_panel`, the screener or the web app, and nothing here should be
until it has cleared that gate.
"""
