import os
import pandas as pd
from flask import render_template, request, jsonify, flash, session
from werkzeug.utils import secure_filename
import tempfile
import logging

from app import db
from models import Candle, PriceActionPattern, FairValueGap, TradeOpportunity
from services.candle_service import process_csv_data, generate_higher_timeframe_candles, link_unlinked_timeframes
from services.price_action_service import identify_price_action_patterns, validate_patterns
from services.fvg_service import identify_fair_value_gaps
from services.trade_service import identify_trade_opportunities, get_trade_statistics

logger = logging.getLogger(__name__)

def register_routes(app):
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/api/upload', methods=['POST'])
    def upload_csv():
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file part'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No selected file'}), 400
            
            if not file.filename.endswith('.csv'):
                return jsonify({'error': 'Only CSV files are allowed'}), 400
            
            symbol = request.form.get('symbol', 'EUR/USD')
            
            # Create temp file to save the uploaded file
            fd, temp_path = tempfile.mkstemp()
            file.save(temp_path)
            
            try:
                # Process the CSV data
                df = pd.read_csv(temp_path)
                
                # Clean existing data for this symbol
                Candle.query.filter_by(symbol=symbol).delete()
                db.session.commit()
                
                # Process the data
                candles = process_csv_data(df, symbol)
                logger.info(f"Processed {len(candles)} 1-minute candles")
                
                # Generate higher timeframe candles
                timeframes = ['5m', '15m', '30m', '1H', '4H']
                for tf in timeframes:
                    higher_tf_candles = generate_higher_timeframe_candles(candles, tf)
                    logger.info(f"Generated {len(higher_tf_candles)} {tf} candles")
                
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Data uploaded and processed successfully',
                    'candleCount': len(candles)
                })
            
            finally:
                os.close(fd)
                os.unlink(temp_path)
        
        except Exception as e:
            logger.error(f"Error processing upload: {str(e)}")
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/candles', methods=['GET'])
    def get_candles():
        try:
            symbol = request.args.get('symbol', 'EUR/USD')
            timeframe = request.args.get('timeframe', '1m')
            
            # Get candles for the specified symbol and timeframe
            candles = Candle.query.filter_by(symbol=symbol, timeframe_str=timeframe).order_by(Candle.timestamp).all()
            
            candle_data = [{
                'id': c.candle_id,
                'time': c.timestamp.timestamp(),
                'open': c.open_price,
                'high': c.high_price,
                'low': c.low_price,
                'close': c.close_price,
                'volume': c.volume
            } for c in candles]
            
            return jsonify(candle_data)
        
        except Exception as e:
            logger.error(f"Error retrieving candles: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/timeframes', methods=['GET'])
    def get_timeframes():
        try:
            symbol = request.args.get('symbol', 'EUR/USD')
            
            # Get all available timeframes for the symbol
            timeframes = db.session.query(Candle.timeframe_str)\
                .filter_by(symbol=symbol)\
                .distinct()\
                .all()
            
            # Count candles in each timeframe
            result = []
            for tf in timeframes:
                timeframe = tf[0]  # Extract the string from the tuple
                count = Candle.query.filter_by(symbol=symbol, timeframe_str=timeframe).count()
                
                # Get parent-child relationships
                linked_count = Candle.query.filter(
                    Candle.symbol == symbol,
                    Candle.timeframe_str == timeframe,
                    Candle.parent_candle_id.isnot(None)
                ).count()
                
                result.append({
                    'timeframe': timeframe,
                    'candleCount': count,
                    'linkedCount': linked_count
                })
            
            return jsonify(result)
        
        except Exception as e:
            logger.error(f"Error retrieving timeframes: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/analyze/price-action', methods=['POST'])
    def analyze_price_action():
        try:
            data = request.json
            symbol = data.get('symbol', 'EUR/USD')
            timeframes = data.get('timeframes', ['5m', '15m', '30m'])
            pivot_tf = data.get('pivotTimeframe', '15m')
            
            # Clear existing price action patterns
            PriceActionPattern.query.delete()
            db.session.commit()
            
            # Identify price action patterns for each timeframe
            patterns_by_tf = {}
            for tf in timeframes:
                patterns = identify_price_action_patterns(symbol, tf)
                patterns_by_tf[tf] = len(patterns)
                logger.info(f"Identified {len(patterns)} patterns for {tf}")
            
            # Validate patterns using the pivot timeframe
            validated_patterns = validate_patterns(symbol, pivot_tf, timeframes)
            
            # Prepare the response
            validation_stats = {
                'valid': PriceActionPattern.query.filter_by(validation_status_str='Valid').count(),
                'invalid': PriceActionPattern.query.filter_by(validation_status_str='Invalid').count(),
                'pending': PriceActionPattern.query.filter_by(validation_status_str='Pending').count()
            }
            
            pattern_counts = {}
            for tf in timeframes:
                pattern_counts[tf] = {
                    'HH': PriceActionPattern.query.filter_by(timeframe_str=tf, pattern_type_str='HH').count(),
                    'HL': PriceActionPattern.query.filter_by(timeframe_str=tf, pattern_type_str='HL').count(),
                    'LH': PriceActionPattern.query.filter_by(timeframe_str=tf, pattern_type_str='LH').count(),
                    'LL': PriceActionPattern.query.filter_by(timeframe_str=tf, pattern_type_str='LL').count(),
                    'BOS': PriceActionPattern.query.filter_by(timeframe_str=tf, pattern_type_str='BOS').count(),
                    'CHoCH': PriceActionPattern.query.filter_by(timeframe_str=tf, pattern_type_str='CHoCH').count()
                }
            
            return jsonify({
                'success': True,
                'message': 'Price action analysis completed',
                'patternsByTimeframe': patterns_by_tf,
                'validationStats': validation_stats,
                'patternCounts': pattern_counts
            })
        
        except Exception as e:
            logger.error(f"Error analyzing price action: {str(e)}")
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/analyze/fvg', methods=['POST'])
    def analyze_fvg():
        try:
            data = request.json
            symbol = data.get('symbol', 'EUR/USD')
            timeframe = data.get('timeframe', '15m')
            
            # Clear existing FVGs
            FairValueGap.query.delete()
            db.session.commit()
            
            # Identify FVGs
            fvgs = identify_fair_value_gaps(symbol, timeframe)
            
            return jsonify({
                'success': True,
                'message': f'Identified {len(fvgs)} Fair Value Gaps for {timeframe}',
                'fvgCount': len(fvgs)
            })
        
        except Exception as e:
            logger.error(f"Error analyzing FVGs: {str(e)}")
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/analyze/opportunities', methods=['POST'])
    def analyze_opportunities():
        try:
            data = request.json
            symbol = data.get('symbol', 'EUR/USD')
            choch_timeframe = data.get('chochTimeframe', '15m')
            fvg_timeframe = data.get('fvgTimeframe', '5m')
            
            # Clear existing trade opportunities
            TradeOpportunity.query.delete()
            db.session.commit()
            
            # Identify trade opportunities
            opportunities = identify_trade_opportunities(symbol, choch_timeframe, fvg_timeframe)
            
            return jsonify({
                'success': True,
                'message': f'Identified {len(opportunities)} trade opportunities',
                'opportunityCount': len(opportunities)
            })
        
        except Exception as e:
            logger.error(f"Error analyzing trade opportunities: {str(e)}")
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/statistics/trades', methods=['GET'])
    def get_trades_statistics():
        try:
            stats = get_trade_statistics()
            return jsonify(stats)
        
        except Exception as e:
            logger.error(f"Error retrieving trade statistics: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/data/patterns', methods=['GET'])
    def get_patterns():
        try:
            timeframe = request.args.get('timeframe', '15m')
            symbol = request.args.get('symbol', 'EUR/USD')
            
            patterns = PriceActionPattern.query.join(Candle, PriceActionPattern.candle_id == Candle.candle_id)\
                .filter(PriceActionPattern.timeframe_str == timeframe, Candle.symbol == symbol)\
                .order_by(Candle.timestamp).all()
            
            pattern_data = []
            for p in patterns:
                candle = Candle.query.get(p.candle_id)
                pattern_data.append({
                    'id': p.pattern_id,
                    'type': p.pattern_type_str,
                    'timeframe': p.timeframe_str,
                    'status': p.validation_status_str,
                    'timestamp': candle.timestamp.timestamp(),
                    'price': candle.close_price
                })
            
            return jsonify(pattern_data)
        
        except Exception as e:
            logger.error(f"Error retrieving patterns: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/data/fvgs', methods=['GET'])
    def get_fvgs():
        try:
            timeframe = request.args.get('timeframe', '15m')
            symbol = request.args.get('symbol', 'EUR/USD')
            
            fvgs = FairValueGap.query.filter_by(timeframe_str=timeframe)\
                .join(Candle, FairValueGap.candle_start_id == Candle.candle_id)\
                .filter(Candle.symbol == symbol)\
                .order_by(Candle.timestamp).all()
            
            fvg_data = []
            for fvg in fvgs:
                start_candle = Candle.query.get(fvg.candle_start_id)
                end_candle = Candle.query.get(fvg.candle_end_id)
                
                fvg_data.append({
                    'id': fvg.fvg_id,
                    'timeframe': fvg.timeframe_str,
                    'startTime': start_candle.timestamp.timestamp(),
                    'endTime': end_candle.timestamp.timestamp(),
                    'startPrice': fvg.start_price,
                    'endPrice': fvg.end_price,
                    'fillPercentage': fvg.fill_percentage
                })
            
            return jsonify(fvg_data)
        
        except Exception as e:
            logger.error(f"Error retrieving FVGs: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/data/opportunities', methods=['GET'])
    def get_opportunities():
        try:
            opportunities = TradeOpportunity.query.order_by(TradeOpportunity.creation_time).all()
            
            opportunity_data = []
            for opp in opportunities:
                pattern = PriceActionPattern.query.get(opp.choch_pattern_id)
                fvg = FairValueGap.query.get(opp.fvg_id)
                
                opportunity_data.append({
                    'id': opp.opportunity_id,
                    'status': opp.status_str,
                    'entryPrice': opp.entry_price,
                    'stopLoss': opp.stop_loss,
                    'takeProfit': opp.take_profit,
                    'creationTime': opp.creation_time.timestamp(),
                    'patternType': pattern.pattern_type_str,
                    'patternTimeframe': pattern.timeframe_str,
                    'fvgTimeframe': fvg.timeframe_str
                })
            
            return jsonify(opportunity_data)
        
        except Exception as e:
            logger.error(f"Error retrieving trade opportunities: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    @app.route('/api/link-timeframes', methods=['POST'])
    def link_timeframes():
        try:
            data = request.json
            symbol = data.get('symbol', 'EUR/USD')
            
            # Run the linking function
            success = link_unlinked_timeframes(symbol)
            
            # Count linked candles for each timeframe
            timeframes = ['5m', '15m', '30m', '1H', '4H']
            linked_counts = {}
            for tf in timeframes:
                linked_count = Candle.query.filter(
                    Candle.symbol == symbol,
                    Candle.timeframe_str == tf,
                    Candle.parent_candle_id.isnot(None)
                ).count()
                
                total_count = Candle.query.filter_by(
                    symbol=symbol,
                    timeframe_str=tf
                ).count()
                
                linked_counts[tf] = {
                    'linked': linked_count,
                    'total': total_count,
                    'percentage': round(linked_count / total_count * 100 if total_count > 0 else 0, 2)
                }
            
            return jsonify({
                'success': success,
                'message': 'Timeframes linked successfully',
                'linkedCounts': linked_counts
            })
        
        except Exception as e:
            logger.error(f"Error linking timeframes: {str(e)}")
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
