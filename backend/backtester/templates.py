"""Backtrader strategy code templates the agent can use as a starting point."""

STRATEGY_TEMPLATE = '''
import backtrader as bt
import json
import sys

class GeneratedStrategy(bt.Strategy):
    """Auto-generated strategy by the Quant Agent."""

    params = (
        {params_block}
    )

    def __init__(self):
        {init_block}

    def next(self):
        {next_block}


def run_backtest(data_csv_path: str, initial_cash: float = 100000.0):
    """Execute the backtest and print JSON results to stdout."""
    cerebro = bt.Cerebro()
    cerebro.addstrategy(GeneratedStrategy)

    # Load data
    data = bt.feeds.GenericCSVData(
        dataname=data_csv_path,
        dtformat="%Y-%m-%d",
        openinterest=-1,
    )
    cerebro.adddata(data)
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)

    # Analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.04)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

    # Run
    results = cerebro.run()
    strat = results[0]

    # Extract metrics
    sharpe_analysis = strat.analyzers.sharpe.get_analysis()
    dd_analysis = strat.analyzers.drawdown.get_analysis()
    trade_analysis = strat.analyzers.trades.get_analysis()
    returns_analysis = strat.analyzers.returns.get_analysis()

    final_value = cerebro.broker.getvalue()
    total_return = (final_value - initial_cash) / initial_cash * 100

    # Collect equity curve
    # (backtrader observers track this internally)
    output = {
        "final_value": round(final_value, 2),
        "initial_cash": initial_cash,
        "total_return": round(total_return, 4),
        "sharpe_ratio": sharpe_analysis.get("sharperatio"),
        "max_drawdown": round(dd_analysis.get("max", {}).get("drawdown", 0), 4),
        "max_drawdown_duration": dd_analysis.get("max", {}).get("len", 0),
        "total_trades": trade_analysis.get("total", {}).get("total", 0),
        "won_trades": trade_analysis.get("won", {}).get("total", 0),
        "lost_trades": trade_analysis.get("lost", {}).get("total", 0),
    }

    print("===BACKTEST_RESULT===")
    print(json.dumps(output))
    print("===END_RESULT===")
    return output


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data.csv"
    cash = float(sys.argv[2]) if len(sys.argv) > 2 else 100000.0
    run_backtest(csv_path, cash)
'''

SMA_CROSSOVER_EXAMPLE = '''
import backtrader as bt
import json
import sys

class GeneratedStrategy(bt.Strategy):
    """SMA Crossover Strategy — buy when fast SMA crosses above slow SMA."""

    params = (
        ("fast_period", 10),
        ("slow_period", 30),
    )

    def __init__(self):
        self.fast_sma = bt.indicators.SMA(self.data.close, period=self.p.fast_period)
        self.slow_sma = bt.indicators.SMA(self.data.close, period=self.p.slow_period)
        self.crossover = bt.indicators.CrossOver(self.fast_sma, self.slow_sma)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.close()


def run_backtest(data_csv_path: str, initial_cash: float = 100000.0):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(GeneratedStrategy)

    data = bt.feeds.GenericCSVData(
        dataname=data_csv_path,
        dtformat="%Y-%m-%d",
        openinterest=-1,
    )
    cerebro.adddata(data)
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.04)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

    results = cerebro.run()
    strat = results[0]

    sharpe_analysis = strat.analyzers.sharpe.get_analysis()
    dd_analysis = strat.analyzers.drawdown.get_analysis()
    trade_analysis = strat.analyzers.trades.get_analysis()

    final_value = cerebro.broker.getvalue()
    total_return = (final_value - initial_cash) / initial_cash * 100

    output = {
        "final_value": round(final_value, 2),
        "initial_cash": initial_cash,
        "total_return": round(total_return, 4),
        "sharpe_ratio": sharpe_analysis.get("sharperatio"),
        "max_drawdown": round(dd_analysis.get("max", {}).get("drawdown", 0), 4),
        "max_drawdown_duration": dd_analysis.get("max", {}).get("len", 0),
        "total_trades": trade_analysis.get("total", {}).get("total", 0),
        "won_trades": trade_analysis.get("won", {}).get("total", 0),
        "lost_trades": trade_analysis.get("lost", {}).get("total", 0),
    }

    print("===BACKTEST_RESULT===")
    print(json.dumps(output))
    print("===END_RESULT===")
    return output


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data.csv"
    cash = float(sys.argv[2]) if len(sys.argv) > 2 else 100000.0
    run_backtest(csv_path, cash)
'''
