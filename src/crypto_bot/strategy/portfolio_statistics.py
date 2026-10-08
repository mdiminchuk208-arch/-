"""Statistics of completed virtual trades; undefined ratios remain JSON null."""
from collections import Counter
from statistics import mean, median


def trade_statistics(trades):
    trades = sorted((t for t in trades if t['status']=='CLOSED'),
                    key=lambda t:(t['exit_time'],t['symbol'],t['trade_id']))
    pnls = [t['net_pnl'] for t in trades]
    rs = [t['result_R'] for t in trades]
    wins = sum(p>1e-9 for p in pnls)
    losses = sum(p< -1e-9 for p in pnls)
    gross_profit = sum(p for p in pnls if p>0)
    gross_loss = -sum(p for p in pnls if p<0)
    win_streak=loss_streak=max_win=max_loss=0
    contribution=peak=dd=0.0
    for p in pnls:
        win_streak=win_streak+1 if p>1e-9 else 0
        loss_streak=loss_streak+1 if p< -1e-9 else 0
        max_win,max_loss=max(max_win,win_streak),max(max_loss,loss_streak)
        contribution+=p
        peak=max(peak,contribution)
        dd=max(dd,peak-contribution)
    return dict(completed_trades=len(trades),wins=wins,losses=losses,
        breakevens=len(trades)-wins-losses,net_pnl=sum(pnls),gross_profit=gross_profit,
        gross_loss=gross_loss,profit_factor=gross_profit/gross_loss if gross_loss else None,
        expectancy=mean(pnls) if pnls else None,average_R=mean(rs) if rs else None,
        median_R=median(rs) if rs else None,win_rate=wins/len(trades) if trades else None,
        loss_rate=losses/len(trades) if trades else None,
        breakeven_rate=(len(trades)-wins-losses)/len(trades) if trades else None,
        longest_win_streak=max_win,longest_loss_streak=max_loss,
        realized_contribution_drawdown_usdt=dd,
        undefined_ratio_policy='NULL_WHEN_NO_TRADES_OR_NO_LOSSES')


def portfolio_statistics(portfolio, signals, symbols):
    trades=list(portfolio.trades.values())
    result=trade_statistics(trades)
    closed=[t for t in trades if t['status']=='CLOSED']
    result.update(starting_balance=portfolio.starting_balance,balance=portfolio.balance,
        final_equity=portfolio.equity,realized_pnl=portfolio.realized_pnl,
        unrealized_pnl=portfolio.unrealized_pnl,net_equity_pnl=portfolio.equity-portfolio.starting_balance,
        return_percent=(portfolio.equity/portfolio.starting_balance-1)*100,
        equity_peak=portfolio.equity_peak,lowest_equity=portfolio.lowest_equity,
        max_drawdown=portfolio.max_drawdown,fees_paid=portfolio.fees_paid,
        slippage_cost=portfolio.slippage_cost,status=portfolio.status,
        open_trades=len(trades)-len(closed),entries=len(trades),
        average_risk_percent=mean(t['risk_percent'] for t in trades) if trades else None,
        max_single_trade_risk_amount=max((t['risk_amount'] for t in trades),default=0),
        max_aggregate_risk_amount=max((t['aggregate_risk_after'] for t in trades),default=0),
        max_aggregate_risk_fraction=max((t['aggregate_risk_fraction_after'] for t in trades),default=0),
        admission_blocks=dict(Counter(d.reason for d in portfolio.journal if d.action=='VIRTUAL_ENTRY_BLOCKED')),
        next_open_deferrals=sum(d.action=='VIRTUAL_ENTRY_DEFERRED' for d in portfolio.journal),
        trade_entry_allowed=False)
    result['by_direction']={side:trade_statistics(t for t in trades if t['direction']==side)
                            for side in ('LONG','SHORT')}
    result['by_symbol']={s:{**trade_statistics(t for t in trades if t['symbol']==s),
        'setups':len({sig.signal_id for sig in signals if sig.symbol==s}),
        'entries':sum(t['symbol']==s for t in trades)} for s in sorted(symbols)}
    result['score_buckets']={label:trade_statistics(t for t in trades if low<=t['score']<=high)
        for label,low,high in (('<75',0,74),('75-79',75,79),('80-84',80,84),
                              ('85-89',85,89),('90-94',90,94),('95-100',95,100))}
    # Ranking without completed trades has no evidence, even if all P&Ls are zero.
    result['best_worst']={}
    for category in ('by_symbol','by_direction','score_buckets'):
        eligible=[(key,value['net_pnl']) for key,value in result[category].items() if value['completed_trades']]
        result['best_worst'][category]=dict(best=max(eligible,key=lambda x:(x[1],x[0]))[0],
            worst=min(eligible,key=lambda x:(x[1],x[0]))[0]) if eligible else dict(best=None,worst=None)
    return result
