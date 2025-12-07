"""Configuration management using environment variables."""

import os
from pathlib import Path
from typing import Optional
from decimal import Decimal
from dotenv import load_dotenv

# Load .env file if it exists
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Import simulation state for runtime overrides
try:
    from config.simulation_state import (
        get_simulation_running,
        get_simulation_speed,
        get_simulation_days,
        get_starting_capital
    )
except ImportError:
    # Fallback if simulation_state module isn't available
    def get_simulation_running(): return False
    def get_simulation_speed(): return 100.0
    def get_simulation_days(): return 30
    def get_starting_capital(): return 1000.0


class Settings:
    """Application settings loaded from environment."""
    
    # Exchange API Keys
    BYBIT_API_KEY: str = os.getenv("BYBIT_API_KEY", "")
    BYBIT_API_SECRET: str = os.getenv("BYBIT_API_SECRET", "")
    BYBIT_TESTNET: bool = os.getenv("BYBIT_TESTNET", "false").lower() == "true"
    
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET: str = os.getenv("BINANCE_API_SECRET", "")
    BINANCE_TESTNET: bool = os.getenv("BINANCE_TESTNET", "false").lower() == "true"
    
    OKX_API_KEY: str = os.getenv("OKX_API_KEY", "")
    OKX_API_SECRET: str = os.getenv("OKX_API_SECRET", "")
    OKX_PASSPHRASE: Optional[str] = os.getenv("OKX_PASSPHRASE")
    OKX_TESTNET: bool = os.getenv("OKX_TESTNET", "false").lower() == "true"
    
    HYPERLIQUID_API_KEY: str = os.getenv("HYPERLIQUID_API_KEY", "")
    HYPERLIQUID_API_SECRET: str = os.getenv("HYPERLIQUID_API_SECRET", "")
    HYPERLIQUID_WALLET: Optional[str] = os.getenv("HYPERLIQUID_WALLET")
    HYPERLIQUID_TESTNET: bool = os.getenv("HYPERLIQUID_TESTNET", "false").lower() == "true"
    
    # Helius API
    HELIUS_API_KEY: str = os.getenv("HELIUS_API_KEY", "")
    
    # Trading Parameters
    STARTING_CAPITAL: Decimal = Decimal(os.getenv("STARTING_CAPITAL", "1000"))
    RISK_APPETITE: Decimal = Decimal(os.getenv("RISK_APPETITE", "0.95"))
    ALLOCATION_PERCENT: Decimal = Decimal(os.getenv("ALLOCATION_PERCENT", "0.95"))
    
    # MEV Settings
    MIN_LIQ_USD: Decimal = Decimal(os.getenv("MIN_LIQ_USD", "40000"))
    MAX_EXECUTE_USD: Decimal = Decimal(os.getenv("MAX_EXECUTE_USD", "12000"))
    MIN_PROFIT_USD: Decimal = Decimal(os.getenv("MIN_PROFIT_USD", "15"))
    
    # Funding Rate Settings
    TOP_N_COINS: int = int(os.getenv("TOP_N_COINS", "3"))
    MIN_FUNDING_RATE: Decimal = Decimal(os.getenv("MIN_FUNDING_RATE", "0.0001"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[Path] = Path(os.getenv("LOG_FILE", "logs/crypto_bot.log")) if os.getenv("LOG_FILE") else None
    
    # Memory/Storage
    MEMORY_DIR: Path = Path(os.getenv("MEMORY_DIR", "data/memory"))
    
    # Paper Trading / Simulation
    PAPER_TRADING: bool = os.getenv("PAPER_TRADING", "true").lower() == "true"
    SIMULATION_MODE: bool = os.getenv("SIMULATION_MODE", "false").lower() == "true"
    SIMULATION_STARTING_BALANCE: Decimal = Decimal(os.getenv("SIMULATION_STARTING_BALANCE", "10000"))
    SIMULATION_FEES: Decimal = Decimal(os.getenv("SIMULATION_FEES", "0.001"))  # 0.1% per trade
    
    # Simulation Control (runtime state via dashboard)
    # These read from simulation_state.json first (runtime override), then .env (defaults)
    @property
    def SIMULATION_RUNNING(self) -> bool:
        """Check if simulation is currently running.
        
        Reads from data/simulation_state.json first (runtime override),
        falls back to .env SIMULATION_RUNNING variable.
        """
        # Runtime state takes precedence
        try:
            return get_simulation_running()
        except Exception:
            # Fallback to .env
            return os.getenv("SIMULATION_RUNNING", "false").lower() == "true"
    
    @property
    def SIMULATION_SPEED(self) -> float:
        """Get simulation speed multiplier.
        
        Reads from data/simulation_state.json first (runtime override),
        falls back to .env SIMULATION_SPEED variable.
        """
        # Runtime state takes precedence
        try:
            return get_simulation_speed()
        except Exception:
            # Fallback to .env
            return float(os.getenv("SIMULATION_SPEED", "100"))
    
    @property
    def SIMULATION_DAYS(self) -> int:
        """Get target simulation duration in days.
        
        Reads from data/simulation_state.json first (runtime override),
        falls back to .env SIMULATION_DAYS variable.
        """
        # Runtime state takes precedence
        try:
            return get_simulation_days()
        except Exception:
            # Fallback to .env
            return int(os.getenv("SIMULATION_DAYS", "30"))
    
    # Risk Controls
    MAX_POSITION_SIZE_USD: Decimal = Decimal(os.getenv("MAX_POSITION_SIZE_USD", "5000"))
    MAX_DAILY_LOSS_PERCENT: Decimal = Decimal(os.getenv("MAX_DAILY_LOSS_PERCENT", "5.0"))
    MAX_DAILY_LOSS_USD: Decimal = Decimal(os.getenv("MAX_DAILY_LOSS_USD", "500"))
    POSITION_RECONCILIATION_INTERVAL: int = int(os.getenv("POSITION_RECONCILIATION_INTERVAL", "300"))  # seconds
    
    # Backtesting
    HISTORICAL_DATA_DIR: Path = Path(os.getenv("HISTORICAL_DATA_DIR", "data/historical"))
    
    # Monitoring
    ENABLE_ALERTS: bool = os.getenv("ENABLE_ALERTS", "false").lower() == "true"
    ALERT_EMAIL: Optional[str] = os.getenv("ALERT_EMAIL")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required settings are present.
        
        Returns:
            True if valid, raises ValueError otherwise
        """
        # At least one exchange must be configured
        exchanges_configured = any([
            cls.BYBIT_API_KEY and cls.BYBIT_API_SECRET,
            cls.BINANCE_API_KEY and cls.BINANCE_API_SECRET,
            cls.OKX_API_KEY and cls.OKX_API_SECRET,
            cls.HYPERLIQUID_API_KEY and cls.HYPERLIQUID_API_SECRET,
        ])
        
        # If paper trading is enabled, we don't need real exchange credentials
        if not cls.PAPER_TRADING and not exchanges_configured:
            raise ValueError(
                "At least one exchange API key/secret must be configured when PAPER_TRADING=false. "
                "Set BYBIT_API_KEY/SECRET, BINANCE_API_KEY/SECRET, OKX_API_KEY/SECRET, "
                "or HYPERLIQUID_API_KEY/SECRET. Or set PAPER_TRADING=true for simulation mode."
            )
            
        return True


# Global settings instance
settings = Settings()

