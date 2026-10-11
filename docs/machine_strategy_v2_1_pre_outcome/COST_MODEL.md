# Cost model

For signed gross price PnL divided by abs(actual fill-fixed initial stop), fee_R=0.0006*(fill+exit)/risk, slippage_R=0.0002*(fill+exit)/risk. Net_R=gross_R-fee_R-slippage_R. Quantity cancels for this explicitly linear proportional model. Funding unavailable/excluded. Closed-primary costs and known entry fees for all FILLED are separate. Preset cost multipliers: 0.5, 1, 2.
