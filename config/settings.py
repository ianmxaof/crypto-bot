"""Configuration management using environment variables."""

import os
from pathlib import Path
from typing import Optional
from decimal import Decimal
from dotenv import load_dotenv

# Load .env file if it exists
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


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
        
        if not exchanges_configured:
            raise ValueError(
                "At least one exchange API key/secret must be configured. "
                "Set BYBIT_API_KEY/SECRET, BINANCE_API_KEY/SECRET, OKX_API_KEY/SECRET, "
                "or HYPERLIQUID_API_KEY/SECRET"
            )
            
        return True


# Global settings instance
settings = Settings()

