# Strategy Engine Architecture

## Core Strategies (Self-Improving)

### 1. **Alpha Momentum Flow**
- **Edge:** Options flow + price action confluence
- **Assets:** Top 50 liquid stocks
- **Timeframe:** 5-30 min
- **Risk:** 1% per trade

### 2. **Mean Reversion v2.0**
- **Edge:** Bollinger Band squeeze + volume spike
- **Filter:** High short interest (>20%)
- **Assets:** Oversold growth stocks
- **Risk:** 2% per trade

### 3. **Earnings Volatility Harvest**
- **Edge:** Post-earnings IV crush + directional bias
- **Entry:** 1-2 hours after earnings
- **Assets:** Stocks with predictable reactions
- **Risk:** 3% per trade

### 4. **Dark Pool Arbitrage**
- **Edge:** Large block trades + retail flow divergence
- **Signal:** >$1M block vs retail sentiment
- **Assets:** HFs accumulation targets
- **Risk:** 1.5% per trade

### 5. **Sentiment Extremes**
- **Edge:** WallStreetBets euphoria/surrender
- **Filter:** Put/call ratio extremes > 1.2
- **Assets:** Meme stocks (GME, AMC, etc)
- **Risk:** 2.5% per trade

## Meta-Learning Layer

### Auto Evolution Process
1. **Hypothesis Generation** - AI proposes strategy variations
2. **Backtesting Sandbox** - Walk-forward testing
3. **Risk-Adjusted Scoring** - Sharpe > 2.0, Max DD < 15%
4. **Live Deployment** - Small size, monitored closely
5. **Performance Decay Detection** - Auto-retire underperformers

## Risk Management

### Portfolio-Level Controls
- **Max Drawdown:** 25% portfolio stop
- **Position Correlation:** < 60% between positions
- **Sector Exposure:** Max 25% per sector
- **Daily Loss Limit:** 3% of portfolio

### Real-time Circuit Breakers
- **Volatility Spike:** Automatic flat positions
- **Market Regime Change:** Strategy rotation
- **Liquidity Crisis:** Only cash market trades