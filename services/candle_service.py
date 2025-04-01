import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

from app import db
from models import Candle, TimeframeEnum

logger = logging.getLogger(__name__)

def process_csv_data(df, symbol):
    """
    Process CSV data and create 1-minute candles
    """
    required_columns = ["timestamp", "open", "high", "low", "close", "volume"]
    
    # Check if all required columns are present
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    # Ensure timestamp is in datetime format
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        except Exception as e:
            raise ValueError(f"Could not convert timestamp column to datetime: {str(e)}")
    
    # Sort by timestamp
    df = df.sort_values('timestamp')
    
    # Create candles
    candles = []
    for _, row in df.iterrows():
        candle = Candle(
            symbol=symbol,
            timeframe_str=TimeframeEnum.M1.value,
            open_price=float(row['open']),
            high_price=float(row['high']),
            low_price=float(row['low']),
            close_price=float(row['close']),
            volume=int(row['volume']),
            timestamp=row['timestamp']
        )
        candles.append(candle)
    
    # Add to database
    db.session.add_all(candles)
    db.session.commit()
    
    return candles

def generate_higher_timeframe_candles(candles, timeframe):
    """
    Generate higher timeframe candles from 1-minute candles
    """
    if not candles:
        return []
    
    # Get all 1-minute candles from the database, sorted by timestamp
    symbol = candles[0].symbol if candles else None
    
    # Get all 1-minute candles from database
    one_min_candles = Candle.query.filter_by(symbol=symbol, timeframe_str=TimeframeEnum.M1.value).order_by(Candle.timestamp).all()
    
    # Map string timeframe to Enum
    timeframe_enum_map = {
        '5m': TimeframeEnum.M5,
        '15m': TimeframeEnum.M15,
        '30m': TimeframeEnum.M30,
        '1H': TimeframeEnum.H1,
        '4H': TimeframeEnum.H4
    }
    
    timeframe_enum = timeframe_enum_map.get(timeframe)
    if not timeframe_enum:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    
    # Calculate the number of 1-minute candles in the higher timeframe
    minutes_in_timeframe = {
        TimeframeEnum.M5: 5,
        TimeframeEnum.M15: 15,
        TimeframeEnum.M30: 30,
        TimeframeEnum.H1: 60,
        TimeframeEnum.H4: 240
    }
    
    interval_minutes = minutes_in_timeframe[timeframe_enum]
    
    # Group candles into the higher timeframe
    higher_tf_candles = []
    
    # Get start time aligned to the timeframe boundary
    if one_min_candles:
        first_candle = one_min_candles[0]
        start_time = first_candle.timestamp.replace(
            second=0, microsecond=0, 
            minute=(first_candle.timestamp.minute // interval_minutes) * interval_minutes
        )
        
        # Group the candles by the timeframe
        current_group = []
        current_time = start_time
        
        for candle in one_min_candles:
            next_time = current_time + timedelta(minutes=interval_minutes)
            
            if candle.timestamp >= next_time:
                # Create a new higher timeframe candle from the current group
                if current_group:
                    higher_tf_candle = create_aggregated_candle(current_group, symbol, timeframe_enum, current_time)
                    higher_tf_candles.append(higher_tf_candle)
                
                # Update the current time and clear the group
                while candle.timestamp >= next_time:
                    current_time = next_time
                    next_time = current_time + timedelta(minutes=interval_minutes)
                
                current_group = [candle]
            else:
                current_group.append(candle)
        
        # Process any remaining candles
        if current_group:
            higher_tf_candle = create_aggregated_candle(current_group, symbol, timeframe_enum, current_time)
            higher_tf_candles.append(higher_tf_candle)
    
    # Add to database
    db.session.add_all(higher_tf_candles)
    db.session.commit()
    
    # Now link each 1-minute candle to its parent higher timeframe candle
    for higher_tf_candle in higher_tf_candles:
        # Find all 1-minute candles within this higher timeframe period
        start_time = higher_tf_candle.timestamp
        end_time = start_time + timedelta(minutes=interval_minutes)
        
        child_candles = Candle.query.filter(
            Candle.symbol == symbol,
            Candle.timeframe_str == TimeframeEnum.M1.value,
            Candle.timestamp >= start_time,
            Candle.timestamp < end_time
        ).all()
        
        # Link each child candle to this higher timeframe candle
        for child in child_candles:
            child.parent_candle_id = higher_tf_candle.candle_id
    
    db.session.commit()
    
    # If we're not at the highest timeframe, link to next higher timeframe
    if timeframe_enum != TimeframeEnum.H4:
        next_higher_timeframes = {
            TimeframeEnum.M5: TimeframeEnum.M15,
            TimeframeEnum.M15: TimeframeEnum.M30,
            TimeframeEnum.M30: TimeframeEnum.H1,
            TimeframeEnum.H1: TimeframeEnum.H4
        }
        next_tf_enum = next_higher_timeframes[timeframe_enum]
        next_tf = {v: k for k, v in timeframe_enum_map.items()}[next_tf_enum]
        next_tf_candles = generate_higher_timeframe_candles(higher_tf_candles, next_tf)
    
    return higher_tf_candles

def create_aggregated_candle(candles, symbol, timeframe_enum, start_time):
    """
    Create an aggregated candle from a group of lower timeframe candles
    """
    if not candles:
        return None
    
    open_price = candles[0].open_price
    close_price = candles[-1].close_price
    high_price = max(c.high_price for c in candles)
    low_price = min(c.low_price for c in candles)
    volume = sum(c.volume for c in candles)
    
    return Candle(
        symbol=symbol,
        timeframe_str=timeframe_enum.value,
        open_price=open_price,
        close_price=close_price,
        high_price=high_price,
        low_price=low_price,
        volume=volume,
        timestamp=start_time
    )

def link_unlinked_timeframes(symbol):
    """
    Link candles across timeframes that haven't been properly linked yet
    """
    logger.info(f"Linking unlinked timeframes for {symbol}")
    
    # Define the hierarchy of timeframes
    timeframe_hierarchy = [
        TimeframeEnum.M1.value,
        TimeframeEnum.M5.value,
        TimeframeEnum.M15.value,
        TimeframeEnum.M30.value,
        TimeframeEnum.H1.value,
        TimeframeEnum.H4.value
    ]
    
    # Link each timeframe to the next higher timeframe
    for i in range(len(timeframe_hierarchy) - 1):
        lower_tf = timeframe_hierarchy[i]
        higher_tf = timeframe_hierarchy[i + 1]
        
        # Calculate minutes in each timeframe
        minutes_in_higher_tf = {
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1H': 60,
            '4H': 240
        }[higher_tf]
        
        # Get all candles in the lower timeframe that aren't linked yet
        unlinked_candles = Candle.query.filter(
            Candle.symbol == symbol,
            Candle.timeframe_str == lower_tf,
            Candle.parent_candle_id.is_(None)
        ).order_by(Candle.timestamp).all()
        
        linked_count = 0
        
        for candle in unlinked_candles:
            # Calculate which higher timeframe candle this should belong to
            candle_time = candle.timestamp
            higher_tf_start = candle_time.replace(
                second=0, microsecond=0,
                minute=(candle_time.minute // minutes_in_higher_tf) * minutes_in_higher_tf
            )
            
            # Find the higher timeframe candle
            higher_tf_candle = Candle.query.filter_by(
                symbol=symbol,
                timeframe_str=higher_tf,
                timestamp=higher_tf_start
            ).first()
            
            if higher_tf_candle:
                # Link this candle to its parent
                candle.parent_candle_id = higher_tf_candle.candle_id
                linked_count += 1
        
        if linked_count > 0:
            logger.info(f"Linked {linked_count} {lower_tf} candles to {higher_tf} candles")
    
    db.session.commit()
    
    return True
