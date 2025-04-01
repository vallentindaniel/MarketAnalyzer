import logging
from sqlalchemy import and_, func
from datetime import timedelta

from app import db
from models import Candle, PriceActionPattern, TimeframeEnum, AnalysisTimeframeEnum, PatternTypeEnum, ValidationStatusEnum

logger = logging.getLogger(__name__)

def identify_price_action_patterns(symbol, timeframe):
    """
    Identify price action patterns for a given symbol and timeframe
    """
    # Map string timeframe to Enum
    timeframe_enum_map = {
        '5m': AnalysisTimeframeEnum.M5,
        '15m': AnalysisTimeframeEnum.M15,
        '30m': AnalysisTimeframeEnum.M30,
        '1H': AnalysisTimeframeEnum.H1
    }
    
    timeframe_enum = timeframe_enum_map.get(timeframe)
    if not timeframe_enum:
        raise ValueError(f"Unsupported timeframe for analysis: {timeframe}")
    
    # Map string timeframe to candle timeframe Enum
    candle_timeframe_map = {
        '5m': TimeframeEnum.M5,
        '15m': TimeframeEnum.M15,
        '30m': TimeframeEnum.M30,
        '1H': TimeframeEnum.H1
    }
    
    candle_tf_enum = candle_timeframe_map.get(timeframe)
    
    # Get candles for the specified symbol and timeframe - using string representation
    candles = Candle.query.filter_by(symbol=symbol, timeframe_str=candle_tf_enum.value).order_by(Candle.timestamp).all()
    
    if len(candles) < 5:
        logger.warning(f"Not enough candles to identify patterns for {symbol} {timeframe}")
        return []
    
    patterns = []
    
    # Identify swing highs and lows
    for i in range(2, len(candles) - 2):
        current = candles[i]
        
        # Check for swing high (HH or LH)
        if (current.high_price > candles[i-1].high_price and 
            current.high_price > candles[i-2].high_price and 
            current.high_price > candles[i+1].high_price and 
            current.high_price > candles[i+2].high_price):
            
            # Find previous swing high
            prev_high = None
            for j in range(i-3, max(0, i-20), -1):
                if (candles[j].high_price > candles[j-1].high_price and 
                    candles[j].high_price > candles[j-2].high_price and 
                    candles[j].high_price > candles[j+1].high_price and 
                    candles[j].high_price > candles[j+2].high_price):
                    prev_high = candles[j]
                    break
            
            if prev_high:
                # Higher High (HH)
                if current.high_price > prev_high.high_price:
                    pattern = PriceActionPattern(
                        candle_id=current.candle_id,
                        pattern_type_str=PatternTypeEnum.HH.value,
                        timeframe_str=timeframe_enum.value,
                        validation_status_str=ValidationStatusEnum.PENDING.value
                    )
                    patterns.append(pattern)
                
                # Lower High (LH)
                elif current.high_price < prev_high.high_price:
                    pattern = PriceActionPattern(
                        candle_id=current.candle_id,
                        pattern_type_str=PatternTypeEnum.LH.value,
                        timeframe_str=timeframe_enum.value,
                        validation_status_str=ValidationStatusEnum.PENDING.value
                    )
                    patterns.append(pattern)
        
        # Check for swing low (LL or HL)
        if (current.low_price < candles[i-1].low_price and 
            current.low_price < candles[i-2].low_price and 
            current.low_price < candles[i+1].low_price and 
            current.low_price < candles[i+2].low_price):
            
            # Find previous swing low
            prev_low = None
            for j in range(i-3, max(0, i-20), -1):
                if (candles[j].low_price < candles[j-1].low_price and 
                    candles[j].low_price < candles[j-2].low_price and 
                    candles[j].low_price < candles[j+1].low_price and 
                    candles[j].low_price < candles[j+2].low_price):
                    prev_low = candles[j]
                    break
            
            if prev_low:
                # Lower Low (LL)
                if current.low_price < prev_low.low_price:
                    pattern = PriceActionPattern(
                        candle_id=current.candle_id,
                        pattern_type_str=PatternTypeEnum.LL.value,
                        timeframe_str=timeframe_enum.value,
                        validation_status_str=ValidationStatusEnum.PENDING.value
                    )
                    patterns.append(pattern)
                
                # Higher Low (HL)
                elif current.low_price > prev_low.low_price:
                    pattern = PriceActionPattern(
                        candle_id=current.candle_id,
                        pattern_type_str=PatternTypeEnum.HL.value,
                        timeframe_str=timeframe_enum.value,
                        validation_status_str=ValidationStatusEnum.PENDING.value
                    )
                    patterns.append(pattern)
    
    # Identify BOS (Break of Structure)
    for i in range(4, len(candles) - 1):
        current = candles[i]
        
        # Bullish BOS
        if (current.close_price > candles[i-1].high_price and
            candles[i-1].high_price > candles[i-2].high_price and
            candles[i-2].high_price > candles[i-3].high_price):
            
            pattern = PriceActionPattern(
                candle_id=current.candle_id,
                pattern_type_str=PatternTypeEnum.BOS.value,
                timeframe_str=timeframe_enum.value,
                validation_status_str=ValidationStatusEnum.PENDING.value
            )
            patterns.append(pattern)
        
        # Bearish BOS
        if (current.close_price < candles[i-1].low_price and
            candles[i-1].low_price < candles[i-2].low_price and
            candles[i-2].low_price < candles[i-3].low_price):
            
            pattern = PriceActionPattern(
                candle_id=current.candle_id,
                pattern_type_str=PatternTypeEnum.BOS.value,
                timeframe_str=timeframe_enum.value,
                validation_status_str=ValidationStatusEnum.PENDING.value
            )
            patterns.append(pattern)
    
    # Identify CHoCH (Change of Character)
    # First, get all HH, HL, LH, LL patterns
    for i in range(len(patterns)):
        pattern = patterns[i]
        if pattern.pattern_type_str in [PatternTypeEnum.HH.value, PatternTypeEnum.HL.value, PatternTypeEnum.LH.value, PatternTypeEnum.LL.value]:
            candle = Candle.query.get(pattern.candle_id)
            
            # Look for patterns that occur after this one
            for j in range(i + 1, len(patterns)):
                next_pattern = patterns[j]
                next_candle = Candle.query.get(next_pattern.candle_id)
                
                # Check if next pattern is at least 5 candles later
                if (next_candle.timestamp - candle.timestamp).total_seconds() < 5 * 60:
                    continue
                
                # Check for CHoCH
                if ((pattern.pattern_type_str == PatternTypeEnum.HH.value and next_pattern.pattern_type_str == PatternTypeEnum.LH.value) or
                    (pattern.pattern_type_str == PatternTypeEnum.HL.value and next_pattern.pattern_type_str == PatternTypeEnum.LL.value) or
                    (pattern.pattern_type_str == PatternTypeEnum.LH.value and next_pattern.pattern_type_str == PatternTypeEnum.HH.value) or
                    (pattern.pattern_type_str == PatternTypeEnum.LL.value and next_pattern.pattern_type_str == PatternTypeEnum.HL.value)):
                    
                    choch_pattern = PriceActionPattern(
                        candle_id=next_candle.candle_id,
                        pattern_type_str=PatternTypeEnum.CHOCH.value,
                        timeframe_str=timeframe_enum.value,
                        validation_status_str=ValidationStatusEnum.PENDING.value
                    )
                    patterns.append(choch_pattern)
    
    # Add all patterns to the database
    db.session.add_all(patterns)
    db.session.commit()
    
    return patterns

def validate_patterns(symbol, pivot_timeframe, timeframes):
    """
    Validate price action patterns against other timeframes
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
    
    pivot_tf_enum = timeframe_enum_map.get(pivot_timeframe)
    if not pivot_tf_enum:
        raise ValueError(f"Unsupported pivot timeframe: {pivot_timeframe}")
    
    # Get all patterns for the pivot timeframe
    pivot_patterns = PriceActionPattern.query.filter_by(timeframe_str=pivot_tf_enum.value).all()
    
    for pattern in pivot_patterns:
        pivot_candle = Candle.query.get(pattern.candle_id)
        
        # Initialize validation counts
        confirmations = 0
        contradictions = 0
        
        # Check other timeframes for confirmation or contradiction
        for tf in timeframes:
            if tf == pivot_timeframe:
                continue
            
            tf_enum = timeframe_enum_map.get(tf)
            candle_tf_enum = candle_timeframe_map.get(tf)
            
            if not tf_enum or not candle_tf_enum:
                logger.warning(f"Skipping unsupported timeframe: {tf}")
                continue
            
            # Get candles from other timeframe that overlap with the pivot candle
            # For higher timeframes, find the candle that contains the pivot candle
            # For lower timeframes, find candles within the pivot candle time window
            
            if compare_timeframes(tf, pivot_timeframe) > 0:  # tf is higher than pivot
                # Find the higher timeframe candle that contains the pivot candle
                higher_tf_candle = find_containing_candle(pivot_candle, candle_tf_enum)
                
                if higher_tf_candle:
                    # Check if this candle has a pattern of the same type
                    higher_patterns = PriceActionPattern.query.filter_by(
                        candle_id=higher_tf_candle.candle_id,
                        pattern_type_str=pattern.pattern_type_str
                    ).all()
                    
                    if higher_patterns:
                        confirmations += 1
                    else:
                        # Check if it has a contradicting pattern
                        contradicting_types = get_contradicting_pattern_types(pattern.pattern_type_str)
                        # Using individual filter_by queries since SQLite doesn't support in_
                        contradicting_patterns = []
                        for c_type in contradicting_types:
                            patterns = PriceActionPattern.query.filter_by(
                                candle_id=higher_tf_candle.candle_id,
                                pattern_type_str=c_type
                            ).all()
                            contradicting_patterns.extend(patterns)
                        
                        if contradicting_patterns:
                            contradictions += 1
            
            else:  # tf is lower than or equal to pivot
                # Find lower timeframe candles within the pivot candle time window
                pivot_timeframe_minutes = get_timeframe_minutes(pivot_timeframe)
                pivot_start_time = pivot_candle.timestamp
                pivot_end_time = pivot_start_time + timedelta(minutes=pivot_timeframe_minutes)
                
                lower_candles = Candle.query.filter(
                    Candle.symbol == symbol,
                    Candle.timeframe_str == candle_tf_enum.value,
                    Candle.timestamp >= pivot_start_time,
                    Candle.timestamp < pivot_end_time
                ).all()
                
                # Check for patterns in these candles
                confirming_count = 0
                contradicting_count = 0
                
                for lower_candle in lower_candles:
                    # Check for confirming patterns
                    confirming_patterns = PriceActionPattern.query.filter_by(
                        candle_id=lower_candle.candle_id,
                        pattern_type_str=pattern.pattern_type_str
                    ).all()
                    
                    if confirming_patterns:
                        confirming_count += 1
                    
                    # Check for contradicting patterns
                    contradicting_types = get_contradicting_pattern_types(pattern.pattern_type_str)
                    # Using individual filter_by queries since SQLite doesn't support in_
                    contradicting_patterns = []
                    for c_type in contradicting_types:
                        patterns = PriceActionPattern.query.filter_by(
                            candle_id=lower_candle.candle_id,
                            pattern_type_str=c_type
                        ).all()
                        contradicting_patterns.extend(patterns)
                    
                    if contradicting_patterns:
                        contradicting_count += 1
                
                # If more confirming than contradicting, consider it a confirmation
                if confirming_count > contradicting_count:
                    confirmations += 1
                elif contradicting_count > confirming_count:
                    contradictions += 1
        
        # Update pattern validation status based on confirmations and contradictions
        if confirmations > contradictions:
            pattern.validation_status_str = ValidationStatusEnum.VALID.value
        else:
            pattern.validation_status_str = ValidationStatusEnum.INVALID.value
    
    db.session.commit()
    
    return pivot_patterns

def find_containing_candle(candle, higher_timeframe_enum):
    """
    Find the higher timeframe candle that contains the given candle
    """
    # Get timeframe values
    candle_tf = candle.timeframe_str
    higher_tf = higher_timeframe_enum.value
    
    lower_tf_minutes = get_timeframe_minutes(candle_tf)
    higher_tf_minutes = get_timeframe_minutes(higher_tf)
    
    # Calculate the start time of the higher timeframe candle
    candle_time = candle.timestamp
    higher_tf_start = candle_time.replace(
        second=0, microsecond=0,
        minute=(candle_time.minute // higher_tf_minutes) * higher_tf_minutes
    )
    
    # Find the higher timeframe candle
    higher_tf_candle = Candle.query.filter_by(
        symbol=candle.symbol,
        timeframe_str=higher_timeframe_enum.value,
        timestamp=higher_tf_start
    ).first()
    
    return higher_tf_candle

def compare_timeframes(tf1, tf2):
    """
    Compare two timeframes
    Returns: 1 if tf1 is higher than tf2, -1 if tf1 is lower than tf2, 0 if equal
    """
    timeframe_order = {'1m': 1, '5m': 5, '15m': 15, '30m': 30, '1H': 60, '4H': 240}
    
    if timeframe_order[tf1] > timeframe_order[tf2]:
        return 1
    elif timeframe_order[tf1] < timeframe_order[tf2]:
        return -1
    else:
        return 0

def get_timeframe_minutes(timeframe):
    """
    Get the number of minutes in a timeframe
    """
    timeframe_minutes = {'1m': 1, '5m': 5, '15m': 15, '30m': 30, '1H': 60, '4H': 240}
    return timeframe_minutes[timeframe]

def get_contradicting_pattern_types(pattern_type_str):
    """
    Get pattern types that contradict the given pattern type string
    """
    # Map enum values to their contradicting pattern type strings
    contradictions = {
        PatternTypeEnum.HH.value: [PatternTypeEnum.LL.value, PatternTypeEnum.LH.value],
        PatternTypeEnum.HL.value: [PatternTypeEnum.LH.value, PatternTypeEnum.LL.value],
        PatternTypeEnum.LH.value: [PatternTypeEnum.HH.value, PatternTypeEnum.HL.value],
        PatternTypeEnum.LL.value: [PatternTypeEnum.HH.value, PatternTypeEnum.HL.value],
        PatternTypeEnum.BOS.value: [],  # BOS doesn't have a direct contradiction
        PatternTypeEnum.CHOCH.value: []  # CHoCH doesn't have a direct contradiction
    }
    
    return contradictions.get(pattern_type_str, [])
