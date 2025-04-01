import logging
from datetime import datetime
from sqlalchemy import and_, func

from app import db
from models import Candle, PriceActionPattern, FairValueGap, TradeOpportunity
from models import TimeframeEnum, AnalysisTimeframeEnum, PatternTypeEnum, ValidationStatusEnum, TradeStatusEnum

logger = logging.getLogger(__name__)

def identify_trade_opportunities(symbol, choch_timeframe, fvg_timeframe):
    """
    Identify trade opportunities based on CHoCH patterns and FVGs
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
    
    choch_tf_enum = timeframe_enum_map.get(choch_timeframe)
    fvg_tf_enum = timeframe_enum_map.get(fvg_timeframe)
    candle_choch_tf_enum = candle_timeframe_map.get(choch_timeframe)
    
    if not choch_tf_enum or not fvg_tf_enum or not candle_choch_tf_enum:
        raise ValueError(f"Unsupported timeframe: choch={choch_timeframe}, fvg={fvg_timeframe}")
    
    # Get all valid CHoCH patterns for the specified timeframe
    choch_patterns = PriceActionPattern.query.join(Candle).\
        filter(Candle.symbol == symbol,
               PriceActionPattern.timeframe == choch_tf_enum,
               PriceActionPattern.pattern_type == PatternTypeEnum.CHOCH,
               PriceActionPattern.validation_status == ValidationStatusEnum.VALID).\
        order_by(Candle.timestamp).all()
    
    opportunities = []
    
    for pattern in choch_patterns:
        # Get the candle where this pattern was identified
        pattern_candle = Candle.query.get(pattern.candle_id)
        
        # Find FVGs on the lower timeframe that occurred after this pattern
        fvgs = FairValueGap.query.join(Candle, FairValueGap.candle_start_id == Candle.candle_id).\
            filter(Candle.symbol == symbol,
                   FairValueGap.timeframe == fvg_tf_enum,
                   Candle.timestamp >= pattern_candle.timestamp).\
            order_by(Candle.timestamp).all()
        
        if fvgs:
            # Take the first FVG that occurs after the CHoCH
            fvg = fvgs[0]
            
            # Create a trade opportunity
            # For risk management, we'll use 1:2 risk-reward ratio
            entry_price, stop_loss, take_profit = calculate_trade_levels(pattern, fvg)
            
            opportunity = TradeOpportunity(
                choch_pattern_id=pattern.pattern_id,
                fvg_id=fvg.fvg_id,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                status=TradeStatusEnum.PENDING,
                creation_time=datetime.utcnow()
            )
            
            opportunities.append(opportunity)
    
    # Add all opportunities to the database
    db.session.add_all(opportunities)
    db.session.commit()
    
    # Simulate trade outcomes
    simulate_trade_outcomes(opportunities)
    
    return opportunities

def calculate_trade_levels(pattern, fvg):
    """
    Calculate entry, stop-loss, and take-profit levels for a trade opportunity
    """
    pattern_candle = Candle.query.get(pattern.candle_id)
    
    # Calculate entry price - use the middle of the FVG
    entry_price = (fvg.start_price + fvg.end_price) / 2
    
    # Calculate stop loss - use the opposite side of the FVG with a small buffer
    if fvg.start_price > fvg.end_price:  # Bullish FVG
        stop_loss = fvg.end_price * 0.999  # Just below the bottom of the FVG
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * 2)  # 1:2 risk-reward ratio
    else:  # Bearish FVG
        stop_loss = fvg.end_price * 1.001  # Just above the top of the FVG
        risk = stop_loss - entry_price
        take_profit = entry_price - (risk * 2)  # 1:2 risk-reward ratio
    
    return entry_price, stop_loss, take_profit

def simulate_trade_outcomes(opportunities):
    """
    Simulate the outcomes of the trade opportunities
    """
    for opportunity in opportunities:
        pattern = PriceActionPattern.query.get(opportunity.choch_pattern_id)
        pattern_candle = Candle.query.get(pattern.candle_id)
        
        # Get the candles after the pattern occurred
        future_candles = Candle.query.filter(
            Candle.symbol == pattern_candle.symbol,
            Candle.timeframe == pattern_candle.timeframe,  # Use the candle's timeframe directly
            Candle.timestamp > pattern_candle.timestamp
        ).order_by(Candle.timestamp).all()
        
        if not future_candles:
            # Not enough future data to simulate
            opportunity.status = TradeStatusEnum.PENDING
            continue
        
        # Check if stop loss or take profit was hit
        stop_loss_hit = False
        take_profit_hit = False
        
        # For a bullish trade (expecting price to go up)
        if opportunity.take_profit > opportunity.entry_price:
            for candle in future_candles:
                # Check if stop loss was hit
                if candle.low_price <= opportunity.stop_loss:
                    stop_loss_hit = True
                    break
                
                # Check if take profit was hit before stop loss
                if candle.high_price >= opportunity.take_profit:
                    take_profit_hit = True
                    break
        
        # For a bearish trade (expecting price to go down)
        else:
            for candle in future_candles:
                # Check if stop loss was hit
                if candle.high_price >= opportunity.stop_loss:
                    stop_loss_hit = True
                    break
                
                # Check if take profit was hit before stop loss
                if candle.low_price <= opportunity.take_profit:
                    take_profit_hit = True
                    break
        
        # Update the opportunity status
        if take_profit_hit:
            opportunity.status = TradeStatusEnum.WIN
        elif stop_loss_hit:
            opportunity.status = TradeStatusEnum.LOSS
        else:
            # No conclusive outcome yet
            opportunity.status = TradeStatusEnum.EXECUTED
    
    db.session.commit()

def get_trade_statistics():
    """
    Get statistics on trade opportunities
    """
    # Count total opportunities
    total_opportunities = TradeOpportunity.query.count()
    
    # Count by status
    pending_count = TradeOpportunity.query.filter_by(status=TradeStatusEnum.PENDING).count()
    executed_count = TradeOpportunity.query.filter_by(status=TradeStatusEnum.EXECUTED).count()
    win_count = TradeOpportunity.query.filter_by(status=TradeStatusEnum.WIN).count()
    loss_count = TradeOpportunity.query.filter_by(status=TradeStatusEnum.LOSS).count()
    
    # Calculate win rate
    completed_trades = win_count + loss_count
    win_rate = (win_count / completed_trades * 100) if completed_trades > 0 else 0
    
    # Calculate expectancy
    # For 1:2 risk-reward, wins gain 2R and losses lose 1R
    expectancy = ((win_count * 2) - loss_count) / completed_trades if completed_trades > 0 else 0
    
    # Group by timeframes
    timeframe_stats = {}
    
    # For each analysis timeframe, collect stats
    for tf_enum in AnalysisTimeframeEnum:
        # Get the corresponding string value for display
        tf_value = tf_enum.value
        
        patterns = db.session.query(
            func.count(TradeOpportunity.opportunity_id).label('count'),
            func.sum(TradeOpportunity.status == TradeStatusEnum.WIN).label('wins'),
            func.sum(TradeOpportunity.status == TradeStatusEnum.LOSS).label('losses')
        ).join(
            PriceActionPattern, 
            TradeOpportunity.choch_pattern_id == PriceActionPattern.pattern_id
        ).filter(
            PriceActionPattern.timeframe == tf_enum
        ).first()
        
        if patterns and patterns.count > 0:
            count, wins, losses = patterns
            total = (wins or 0) + (losses or 0)
            win_rate_tf = (wins / total * 100) if total > 0 else 0
            timeframe_stats[tf_value] = {
                'count': count,
                'wins': wins or 0,
                'losses': losses or 0,
                'winRate': round(win_rate_tf, 2)
            }
    
    return {
        'totalOpportunities': total_opportunities,
        'pendingCount': pending_count,
        'executedCount': executed_count,
        'winCount': win_count,
        'lossCount': loss_count,
        'winRate': round(win_rate, 2),
        'expectancy': round(expectancy, 2),
        'timeframeStats': timeframe_stats
    }
