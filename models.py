from datetime import datetime
import enum
from sqlalchemy import String, DateTime, Float, Integer, ForeignKey
from app import db

# Define Enum types
class TimeframeEnum(enum.Enum):
    M1 = '1m'
    M5 = '5m'
    M15 = '15m'
    M30 = '30m'
    H1 = '1H'
    H4 = '4H'

class AnalysisTimeframeEnum(enum.Enum):
    M5 = '5m'
    M15 = '15m'
    M30 = '30m'
    H1 = '1H'

class PatternTypeEnum(enum.Enum):
    HH = 'HH'
    HL = 'HL'
    LH = 'LH'
    LL = 'LL'
    BOS = 'BOS'
    CHOCH = 'CHoCH'

class ValidationStatusEnum(enum.Enum):
    VALID = 'Valid'
    INVALID = 'Invalid'
    PENDING = 'Pending'

class TradeStatusEnum(enum.Enum):
    PENDING = 'Pending'
    EXECUTED = 'Executed'
    CANCELED = 'Canceled'
    WIN = 'Win'
    LOSS = 'Loss'

class Candle(db.Model):
    __tablename__ = 'candles'
    
    candle_id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    timeframe = db.Column(db.Enum(TimeframeEnum), nullable=False)
    open_price = db.Column(db.Float, nullable=False)
    close_price = db.Column(db.Float, nullable=False)
    high_price = db.Column(db.Float, nullable=False)
    low_price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    
    @property
    def timeframe_str(self):
        return self.timeframe.value if self.timeframe else None
    
    @timeframe_str.setter
    def timeframe_str(self, value):
        if value:
            self.timeframe = TimeframeEnum(value)
    
    # Self-referential relationship for linking to parent candle
    parent_candle_id = db.Column(db.Integer, db.ForeignKey('candles.candle_id', ondelete='CASCADE'), nullable=True)
    child_candles = db.relationship('Candle', 
                                    backref=db.backref('parent_candle', remote_side=[candle_id]),
                                    cascade="all, delete-orphan")
    
    # Relationship with PriceActionPattern
    price_action_patterns = db.relationship('PriceActionPattern', backref='candle', cascade="all, delete-orphan")
    
    # Relationship with FairValueGap
    fvg_starts = db.relationship('FairValueGap', 
                                foreign_keys='FairValueGap.candle_start_id',
                                backref='start_candle', cascade="all, delete-orphan")
    fvg_ends = db.relationship('FairValueGap', 
                              foreign_keys='FairValueGap.candle_end_id',
                              backref='end_candle', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Candle {self.symbol} {self.timeframe_str} {self.timestamp}>"


class PriceActionPattern(db.Model):
    __tablename__ = 'price_action_patterns'
    
    pattern_id = db.Column(db.Integer, primary_key=True)
    candle_id = db.Column(db.Integer, db.ForeignKey('candles.candle_id', ondelete='CASCADE'), nullable=False)
    pattern_type = db.Column(db.Enum(PatternTypeEnum), nullable=False)
    timeframe = db.Column(db.Enum(AnalysisTimeframeEnum), nullable=False)
    validation_status = db.Column(db.Enum(ValidationStatusEnum), default=ValidationStatusEnum.PENDING, nullable=False)
    
    @property
    def pattern_type_str(self):
        return self.pattern_type.value if self.pattern_type else None
    
    @pattern_type_str.setter
    def pattern_type_str(self, value):
        if value:
            self.pattern_type = PatternTypeEnum(value)
    
    @property
    def timeframe_str(self):
        return self.timeframe.value if self.timeframe else None
    
    @timeframe_str.setter
    def timeframe_str(self, value):
        if value:
            self.timeframe = AnalysisTimeframeEnum(value)
    
    @property
    def validation_status_str(self):
        return self.validation_status.value if self.validation_status else None
    
    @validation_status_str.setter
    def validation_status_str(self, value):
        if value:
            self.validation_status = ValidationStatusEnum(value)
    
    # Relationship with FairValueGap
    fvgs = db.relationship('FairValueGap', backref='pattern', cascade="all, delete-orphan")
    
    # Relationship with TradeOpportunity
    trade_opportunities = db.relationship('TradeOpportunity', 
                                         foreign_keys='TradeOpportunity.choch_pattern_id',
                                         backref='choch_pattern', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<PriceActionPattern {self.pattern_type.value} {self.timeframe.value} ID:{self.pattern_id}>"


class FairValueGap(db.Model):
    __tablename__ = 'fair_value_gaps'
    
    fvg_id = db.Column(db.Integer, primary_key=True)
    pattern_id = db.Column(db.Integer, db.ForeignKey('price_action_patterns.pattern_id', ondelete='CASCADE'), nullable=False)
    candle_start_id = db.Column(db.Integer, db.ForeignKey('candles.candle_id', ondelete='CASCADE'), nullable=False)
    candle_end_id = db.Column(db.Integer, db.ForeignKey('candles.candle_id', ondelete='CASCADE'), nullable=False)
    start_price = db.Column(db.Float, nullable=False)
    end_price = db.Column(db.Float, nullable=False)
    fill_percentage = db.Column(db.Float, default=0.0, nullable=False)
    timeframe = db.Column(db.Enum(AnalysisTimeframeEnum), nullable=False)
    
    @property
    def timeframe_str(self):
        return self.timeframe.value if self.timeframe else None
    
    @timeframe_str.setter
    def timeframe_str(self, value):
        if value:
            self.timeframe = AnalysisTimeframeEnum(value)
    
    # Relationship with TradeOpportunity
    trade_opportunities = db.relationship('TradeOpportunity', 
                                         foreign_keys='TradeOpportunity.fvg_id',
                                         backref='fvg', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<FairValueGap {self.timeframe.value} {self.start_price}-{self.end_price} ID:{self.fvg_id}>"


class TradeOpportunity(db.Model):
    __tablename__ = 'trade_opportunities'
    
    opportunity_id = db.Column(db.Integer, primary_key=True)
    choch_pattern_id = db.Column(db.Integer, db.ForeignKey('price_action_patterns.pattern_id', ondelete='CASCADE'), nullable=False)
    fvg_id = db.Column(db.Integer, db.ForeignKey('fair_value_gaps.fvg_id', ondelete='CASCADE'), nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    stop_loss = db.Column(db.Float, nullable=False)
    take_profit = db.Column(db.Float, nullable=False)
    status = db.Column(db.Enum(TradeStatusEnum), default=TradeStatusEnum.PENDING, nullable=False)
    creation_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    @property
    def status_str(self):
        return self.status.value if self.status else None
    
    @status_str.setter
    def status_str(self, value):
        if value:
            self.status = TradeStatusEnum(value)
    
    def __repr__(self):
        return f"<TradeOpportunity ID:{self.opportunity_id} Status:{self.status.value}>"
