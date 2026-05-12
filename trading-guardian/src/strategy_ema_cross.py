import pandas as pd
import numpy as np

class EMAStrategy:
    def __init__(self, short_window=50, long_window=200):
        self.short_window = short_window
        self.long_window = long_window

    def get_signal(self, symbol, current_price, qty):
        """
        Simplified signal for StrategyEngine integration.
        Returns a signal dict or None.
        """
        # Placeholder logic for testing
        return {
            'signal': 'HOLD',
            'confidence': 0.5,
            'reason': 'EMA strategy in standby'
        }

    def generate_signals(self, data):
        """
        Generates signals based on EMA 50/200 crossover.
        """
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0.0

        # Calculate EMAs
        signals['short_ema'] = data['close'].ewm(span=self.short_window, adjust=False).mean()
        signals['long_ema'] = data['close'].ewm(span=self.long_window, adjust=False).mean()

        # Create signals
        signals['signal'][self.short_window:] = np.where(
            signals['short_ema'][self.short_window:] > signals['long_ema'][self.short_window:], 1.0, 0.0
        )

        # Generate trading orders
        signals['positions'] = signals['signal'].diff()

        return signals
