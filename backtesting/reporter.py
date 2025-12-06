"""Generate backtest reports."""

import logging
from typing import Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class BacktestReporter:
    """Generate human-readable backtest reports."""
    
    @staticmethod
    def generate_report(results: Dict, output_path: Optional[Path] = None) -> str:
        """Generate a formatted backtest report.
        
        Args:
            results: Backtest results dictionary
            output_path: Optional path to save report
            
        Returns:
            Formatted report string
        """
        metrics = results.get("metrics", {})
        
        report_lines = [
            "=" * 80,
            "BACKTEST REPORT",
            "=" * 80,
            "",
            f"Period: {results.get('start_date', 'N/A')} to {results.get('end_date', 'N/A')}",
            "",
            "PERFORMANCE METRICS",
            "-" * 80,
            f"Initial Capital:     ${metrics.get('initial_capital', 0):,.2f}",
            f"Final Value:         ${metrics.get('final_value', 0):,.2f}",
            f"Total Return:        {metrics.get('total_return_pct', 0):.2f}%",
            f"Max Drawdown:        {metrics.get('max_drawdown_pct', 0):.2f}%",
            "",
            "RISK-ADJUSTED METRICS",
            "-" * 80,
            f"Sharpe Ratio:        {metrics.get('sharpe_ratio', 0):.2f}",
            f"Sortino Ratio:       {metrics.get('sortino_ratio', 0):.2f}",
            "",
            "TRADE STATISTICS",
            "-" * 80,
            f"Total Trades:        {metrics.get('total_trades', 0)}",
            f"Winning Trades:      {metrics.get('winning_trades', 0)}",
            f"Losing Trades:       {metrics.get('losing_trades', 0)}",
            f"Win Rate:            {metrics.get('win_rate', 0) * 100:.2f}%",
            f"Average Win:         ${metrics.get('avg_win', 0):,.2f}",
            f"Average Loss:        ${metrics.get('avg_loss', 0):,.2f}",
            f"Profit Factor:       {metrics.get('profit_factor', 0):.2f}",
            f"Largest Win:         ${metrics.get('largest_win', 0):,.2f}",
            f"Largest Loss:        ${metrics.get('largest_loss', 0):,.2f}",
            "",
            "=" * 80
        ]
        
        report = "\n".join(report_lines)
        
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(report)
            logger.info(f"Report saved to {output_path}")
            
        return report

