import logging
from app import db
from models import Candle, PriceActionPattern, FairValueGap, TimeframeEnum, AnalysisTimeframeEnum

logger = logging.getLogger(__name__)

def identify_fair_value_gaps(symbol, timeframe):
    """
    Identify Fair Value Gaps (FVGs) for a given symbol and timeframe
    """
    # Map string timeframe to Enum
    timeframe_enum_map = {
        '5m': AnalysisTimeframeEnum.M5,
        '15m': AnalysisTimeframeEnum.M15,
        '30m': AnalysisTimeframeEnum.M30,
        '1H': AnalysisTimeframeEnum.H1
    }
    
    # Map string timeframe to candle timeframe Enum
    candle_timeframe_map = {
        '5m': TimeframeEnum.M5,
        '15m': TimeframeEnum.M15,
        '30m': TimeframeEnum.M30,
        '1H': TimeframeEnum.H1
    }
    
    timeframe_enum = timeframe_enum_map.get(timeframe)
    candle_tf_enum = candle_timeframe_map.get(timeframe)
    
    if not timeframe_enum or not candle_tf_enum:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    
    # Get candles for the specified symbol and timeframe
    candles = Candle.query.filter_by(symbol=symbol, timeframe=candle_tf_enum).order_by(Candle.timestamp).all()
    
    if len(candles) < 3:
        logger.warning(f"Not enough candles to identify FVGs for {symbol} {timeframe}")
        return []
    
    fvgs = []
    
    # Find all price action patterns for this timeframe
    patterns = PriceActionPattern.query.filter_by(timeframe=timeframe_enum).all()
    pattern_map = {p.candle_id: p for p in patterns}
    
    # Look for FVGs in the candle data
    for i in range(len(candles) - 2):
        candle1 = candles[i]
        candle2 = candles[i + 1]
        candle3 = candles[i + 2]
        
        # Check for bullish FVG: candle1's low > candle3's high
        if candle1.low_price > candle3.high_price:
            # Find associated pattern
            pattern_id = None
            for j in range(i, i + 3):
                if candles[j].candle_id in pattern_map:
                    pattern_id = pattern_map[candles[j].candle_id].pattern_id
                    break
            
            if pattern_id is None:
                # Use a recent pattern if one isn't directly associated
                recent_pattern = PriceActionPattern.query.join(Candle).\
                    filter(Candle.symbol == symbol, 
                           Candle.timeframe == candle_tf_enum,
                           PriceActionPattern.timeframe == timeframe_enum,
                           Candle.timestamp < candle1.timestamp).\
                    order_by(Candle.timestamp.desc()).first()
                
                if recent_pattern:
                    pattern_id = recent_pattern.pattern_id
            
            if pattern_id:
                # Create bullish FVG
                fvg = FairValueGap(
                    pattern_id=pattern_id,
                    candle_start_id=candle1.candle_id,
                    candle_end_id=candle3.candle_id,
                    start_price=candle1.low_price,
                    end_price=candle3.high_price,
                    fill_percentage=0.0,
                    timeframe=timeframe_enum
                )
                fvgs.append(fvg)
        
        # Check for bearish FVG: candle3's low > candle1's high
        if candle3.low_price > candle1.high_price:
            # Find associated pattern
            pattern_id = None
            for j in range(i, i + 3):
                if candles[j].candle_id in pattern_map:
                    pattern_id = pattern_map[candles[j].candle_id].pattern_id
                    break
            
            if pattern_id is None:
                # Use a recent pattern if one isn't directly associated
                recent_pattern = PriceActionPattern.query.join(Candle).\
                    filter(Candle.symbol == symbol, 
                           Candle.timeframe == candle_tf_enum,
                           PriceActionPattern.timeframe == timeframe_enum,
                           Candle.timestamp < candle1.timestamp).\
                    order_by(Candle.timestamp.desc()).first()
                
                if recent_pattern:
                    pattern_id = recent_pattern.pattern_id
            
            if pattern_id:
                # Create bearish FVG
                fvg = FairValueGap(
                    pattern_id=pattern_id,
                    candle_start_id=candle1.candle_id,
                    candle_end_id=candle3.candle_id,
                    start_price=candle3.low_price,
                    end_price=candle1.high_price,
                    fill_percentage=0.0,
                    timeframe=timeframe_enum
                )
                fvgs.append(fvg)
    
    # Calculate fill percentage for each FVG
    for fvg in fvgs:
        calculate_fvg_fill_percentage(fvg, candles)
    
    # Add all FVGs to the database
    db.session.add_all(fvgs)
    db.session.commit()
    
    return fvgs

def calculate_fvg_fill_percentage(fvg, candles):
    """
    Calculate the fill percentage for a Fair Value Gap
    """
    start_candle = Candle.query.get(fvg.candle_start_id)
    end_candle = Candle.query.get(fvg.candle_end_id)
    
    # Get all candles after the end candle
    subsequent_candles = [c for c in candles if c.timestamp > end_candle.timestamp]
    
    if not subsequent_candles:
        fvg.fill_percentage = 0.0
        return
    
    # Calculate the gap size
    gap_size = abs(fvg.start_price - fvg.end_price)
    
    if gap_size == 0:
        fvg.fill_percentage = 100.0
        return
    
    # Find the maximum penetration into the gap
    max_penetration = 0.0
    
    for candle in subsequent_candles:
        # For bullish FVG (start_price > end_price)
        if fvg.start_price > fvg.end_price:
            # Check if price went down into the gap
            if candle.low_price < fvg.start_price:
                penetration = min(fvg.start_price - candle.low_price, gap_size)
                max_penetration = max(max_penetration, penetration)
        
        # For bearish FVG (end_price > start_price)
        else:
            # Check if price went up into the gap
            if candle.high_price > fvg.start_price:
                penetration = min(candle.high_price - fvg.start_price, gap_size)
                max_penetration = max(max_penetration, penetration)
    
    # Calculate fill percentage
    fvg.fill_percentage = (max_penetration / gap_size) * 100.0
