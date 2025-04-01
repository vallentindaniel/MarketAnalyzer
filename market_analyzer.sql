-- market_analyzer.sql
-- SQL schema for the Market Analyzer application

-- Drop tables if they exist (in reverse order of dependencies)
DROP TABLE IF EXISTS trade_opportunities;
DROP TABLE IF EXISTS fair_value_gaps;
DROP TABLE IF EXISTS price_action_patterns;
DROP TABLE IF EXISTS candles;

-- Create Candles table
CREATE TABLE candles (
    candle_id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    timeframe_str VARCHAR(10) NOT NULL,
    open_price FLOAT NOT NULL,
    close_price FLOAT NOT NULL,
    high_price FLOAT NOT NULL,
    low_price FLOAT NOT NULL,
    volume INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    parent_candle_id INTEGER REFERENCES candles(candle_id) ON DELETE CASCADE
);

-- Create Price Action Patterns table
CREATE TABLE price_action_patterns (
    pattern_id SERIAL PRIMARY KEY,
    candle_id INTEGER NOT NULL REFERENCES candles(candle_id) ON DELETE CASCADE,
    pattern_type_str VARCHAR(10) NOT NULL,
    timeframe_str VARCHAR(10) NOT NULL,
    validation_status_str VARCHAR(10) NOT NULL DEFAULT 'Pending'
);

-- Create Fair Value Gaps table
CREATE TABLE fair_value_gaps (
    fvg_id SERIAL PRIMARY KEY,
    pattern_id INTEGER NOT NULL REFERENCES price_action_patterns(pattern_id) ON DELETE CASCADE,
    candle_start_id INTEGER NOT NULL REFERENCES candles(candle_id) ON DELETE CASCADE,
    candle_end_id INTEGER NOT NULL REFERENCES candles(candle_id) ON DELETE CASCADE,
    start_price FLOAT NOT NULL,
    end_price FLOAT NOT NULL,
    fill_percentage FLOAT NOT NULL DEFAULT 0.0,
    timeframe_str VARCHAR(10) NOT NULL
);

-- Create Trade Opportunities table
CREATE TABLE trade_opportunities (
    opportunity_id SERIAL PRIMARY KEY,
    choch_pattern_id INTEGER NOT NULL REFERENCES price_action_patterns(pattern_id) ON DELETE CASCADE,
    fvg_id INTEGER NOT NULL REFERENCES fair_value_gaps(fvg_id) ON DELETE CASCADE,
    entry_price FLOAT NOT NULL,
    stop_loss FLOAT NOT NULL,
    take_profit FLOAT NOT NULL,
    status_str VARCHAR(10) NOT NULL DEFAULT 'Pending',
    creation_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
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