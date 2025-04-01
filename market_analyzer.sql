-- market_analyzer.sql
-- SQL schema for the Market Analyzer application - MySQL Version

-- Drop tables if they exist (in reverse order of dependencies)
DROP TABLE IF EXISTS trade_opportunities;
DROP TABLE IF EXISTS fair_value_gaps;
DROP TABLE IF EXISTS price_action_patterns;
DROP TABLE IF EXISTS candles;

-- Create Candles table
CREATE TABLE candles (
    candle_id INT AUTO_INCREMENT PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    timeframe_str VARCHAR(10) NOT NULL,
    open_price FLOAT NOT NULL,
    close_price FLOAT NOT NULL,
    high_price FLOAT NOT NULL,
    low_price FLOAT NOT NULL,
    volume INT NOT NULL,
    timestamp DATETIME NOT NULL,
    parent_candle_id INT,
    FOREIGN KEY (parent_candle_id) REFERENCES candles(candle_id) ON DELETE CASCADE
);

-- Create Price Action Patterns table
CREATE TABLE price_action_patterns (
    pattern_id INT AUTO_INCREMENT PRIMARY KEY,
    candle_id INT NOT NULL,
    pattern_type_str VARCHAR(10) NOT NULL,
    timeframe_str VARCHAR(10) NOT NULL,
    validation_status_str VARCHAR(10) NOT NULL DEFAULT 'Pending',
    FOREIGN KEY (candle_id) REFERENCES candles(candle_id) ON DELETE CASCADE
);

-- Create Fair Value Gaps table
CREATE TABLE fair_value_gaps (
    fvg_id INT AUTO_INCREMENT PRIMARY KEY,
    pattern_id INT NOT NULL,
    candle_start_id INT NOT NULL,
    candle_end_id INT NOT NULL,
    start_price FLOAT NOT NULL,
    end_price FLOAT NOT NULL,
    fill_percentage FLOAT NOT NULL DEFAULT 0.0,
    timeframe_str VARCHAR(10) NOT NULL,
    FOREIGN KEY (pattern_id) REFERENCES price_action_patterns(pattern_id) ON DELETE CASCADE,
    FOREIGN KEY (candle_start_id) REFERENCES candles(candle_id) ON DELETE CASCADE,
    FOREIGN KEY (candle_end_id) REFERENCES candles(candle_id) ON DELETE CASCADE
);

-- Create Trade Opportunities table
CREATE TABLE trade_opportunities (
    opportunity_id INT AUTO_INCREMENT PRIMARY KEY,
    choch_pattern_id INT NOT NULL,
    fvg_id INT NOT NULL,
    entry_price FLOAT NOT NULL,
    stop_loss FLOAT NOT NULL,
    take_profit FLOAT NOT NULL,
    status_str VARCHAR(10) NOT NULL DEFAULT 'Pending',
    creation_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (choch_pattern_id) REFERENCES price_action_patterns(pattern_id) ON DELETE CASCADE,
    FOREIGN KEY (fvg_id) REFERENCES fair_value_gaps(fvg_id) ON DELETE CASCADE
);

-- Create indexes for better query performance
CREATE INDEX idx_candles_symbol_timeframe ON candles(symbol, timeframe_str);
CREATE INDEX idx_candles_timestamp ON candles(timestamp);
CREATE INDEX idx_candles_parent ON candles(parent_candle_id);
CREATE INDEX idx_patterns_candle ON price_action_patterns(candle_id);
CREATE INDEX idx_patterns_type_timeframe ON price_action_patterns(pattern_type_str, timeframe_str);
CREATE INDEX idx_fvg_pattern ON fair_value_gaps(pattern_id);
CREATE INDEX idx_fvg_timeframe ON fair_value_gaps(timeframe_str);
CREATE INDEX idx_trades_pattern ON trade_opportunities(choch_pattern_id);
CREATE INDEX idx_trades_fvg ON trade_opportunities(fvg_id);
CREATE INDEX idx_trades_status ON trade_opportunities(status_str);