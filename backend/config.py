
import os

from dotenv import load_dotenv



load_dotenv()





class Config:

    # Ports

    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8899"))

    WS_PORT: int = int(os.getenv("WS_PORT", "8898"))



    # Polymarket

    POLYMARKET_API_KEY: str = os.getenv("POLYMARKET_API_KEY", "")

    POLYMARKET_API_SECRET: str = os.getenv("POLYMARKET_API_SECRET", "")

    POLYMARKET_PASSPHRASE: str = os.getenv("POLYMARKET_PASSPHRASE", "")

    POLYMARKET_WALLET_ADDRESS: str = os.getenv("POLYMARKET_WALLET_ADDRESS", "")

    POLYMARKET_PRIVATE_KEY: str = os.getenv("POLYMARKET_PRIVATE_KEY", "")

    POLYMARKET_BASE_URL: str = "https://clob.polymarket.com"



    # NOAA

    NOAA_API_TOKEN: str = os.getenv("NOAA_API_TOKEN", "")

    NOAA_BASE_URL: str = "https://api.weather.gov"



    # Binance

    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")

    BINANCE_API_SECRET: str = os.getenv("BINANCE_API_SECRET", "")



    # News

    NEWSAPI_KEY: str = os.getenv("NEWSAPI_KEY", "")

    TWITTER_BEARER_TOKEN: str = os.getenv("TWITTER_BEARER_TOKEN", "")



    # Notifications

    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")



    # Risk

    MAX_POSITION_SIZE: float = float(os.getenv("MAX_POSITION_SIZE", "50"))

    MAX_DAILY_LOSS: float = float(os.getenv("MAX_DAILY_LOSS", "200"))

    MIN_EDGE_THRESHOLD: float = float(os.getenv("MIN_EDGE_THRESHOLD", "0.06"))

    MAX_CONCURRENT_POSITIONS: int = int(os.getenv("MAX_CONCURRENT_POSITIONS", "20"))

    STOP_LOSS_PERCENT: float = float(os.getenv("STOP_LOSS_PERCENT", "0.15"))

    DAILY_DRAWDOWN_LIMIT: float = float(os.getenv("DAILY_DRAWDOWN_LIMIT", "0.15"))



    # Simulated starting balance (user-configurable)

    INITIAL_BALANCE: float = float(os.getenv("INITIAL_BALANCE", "150"))



    # Agent scan intervals (seconds) - minimums enforced

    WEATHER_INTERVAL: int = int(os.getenv("WEATHER_INTERVAL", "600"))

    CRYPTO_INTERVAL: int = int(os.getenv("CRYPTO_INTERVAL", "90"))

    POLITICS_INTERVAL: int = int(os.getenv("POLITICS_INTERVAL", "90"))

    SPORTS_INTERVAL: int = int(os.getenv("SPORTS_INTERVAL", "90"))

    ENDGAME_INTERVAL: int = int(os.getenv("ENDGAME_INTERVAL", "30"))



    # Minimum intervals to avoid rate limiting

    MIN_SCAN_INTERVAL: int = 15  # absolute minimum 15 seconds

    MIN_WEATHER_INTERVAL: int = 120  # NOAA rate limit

    MIN_API_INTERVAL: int = 30  # general API rate limit



    # Database

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./polymarket_bot.db")



    # Security

    DASHBOARD_PASSWORD: str = os.getenv("DASHBOARD_PASSWORD", "admin123")

    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me")



    # Mode

    DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() == "true"

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")





config = Config()

